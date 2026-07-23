"""Maker–checker generation of NEW drill sentences for a grammar point (Part C).

When a form needs more drills than are authored (the Gym asking for a bigger
set, or filling a low-density language), draft candidates with the model, then
VERIFY every one before it can enter the pool:

  Maker   — given the point (title, explanation, a few existing drills as
            style, the target language) drafts N fill-in-the-blank drills:
            {sentence with {{answer}}, answer, translation, hint}.
  Checker — each candidate must clear the SAME guards a human edit does
            (services/drills.answerability + the leak/format guards) before it
            is accepted. Whatever fails is dropped, never stored.

Accepted drills are persisted tagged source='ai' with the model in
origin_detail (WP38 provenance) and reviewed=false, so a human still gates
them into learners' view (§6: generated content is never self-certified).

Models resolve through the WP39 registry ('grammar_maker' / 'grammar_checker').
Dev-mock (TUTOR_DEV_MOCK) returns deterministic candidates so the whole
pipeline is testable with no API key — same convention as services/translate.py.
"""

from __future__ import annotations

import json
import re

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.drills import validate_drill
from backend.services.models import resolve_model
from backend.services.nlp import get_nlp

_DRILL_SCHEMA = {
    "type": "object",
    "properties": {
        "drills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence": {
                        "type": "string",
                        "description": "One sentence containing the literal "
                        "{{answer}} blank where the target form goes.",
                    },
                    "answer": {
                        "type": "string",
                        "description": "The single word/word-form that fills the "
                        "blank. One token, never appearing elsewhere in the sentence.",
                    },
                    "translation": {"type": "string"},
                    "hint": {
                        "type": "string",
                        "description": "A short cue that does NOT contain the answer.",
                    },
                },
                "required": ["sentence", "answer", "translation", "hint"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["drills"],
    "additionalProperties": False,
}


def generation_available() -> bool:
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(settings, "tutor_dev_mock", False)


def _mock_drills(point: dict, n: int) -> list[dict]:
    """Deterministic candidates for dev/testing. The first is deliberately
    malformed (answer leaks into the frame) so the checker's reject path is
    exercised, mirroring services/translate.py's mock."""
    out = [{
        "sentence": "The word gato {{answer}} here.",  # 'gato' leaks -> rejected
        "answer": "gato",
        "translation": "The word cat here.",
        "hint": "a pet",
    }]
    for i in range(1, n):
        out.append({
            "sentence": f"Mock sentence {i} with a {{{{answer}}}} in it.",
            "answer": f"palabra{i}",
            "translation": f"Mock translation {i}.",
            "hint": "a cue that hides the answer",
        })
    return out[:n]


async def make_drills(
    point: dict, n: int, language: str, model: str | None = None
) -> list[dict]:
    """Draft N candidate drills for a grammar point.

    *point*: {title, explanation, examples: [existing drill sentences]}.
    Returns raw candidate dicts (unverified) — always run them through
    check_drills() before storing.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_drills(point, n)
    examples = "\n".join(f"  - {s}" for s in (point.get("examples") or [])[:6])
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("grammar_maker", language),
        max_tokens=2048,
        system=(
            f"You author fill-in-the-blank grammar drills in {language} for a "
            f"spaced-repetition app. Produce {n} NEW drills for the grammar point "
            f'"{point.get("title")}". Vary the person, tense, and vocabulary; keep '
            f"each natural and unambiguous. Rules, strictly: the sentence contains "
            f"the literal token {{{{answer}}}} exactly once where the target form "
            f"goes; the answer is a SINGLE word/word-form; the answer must NOT "
            f"appear anywhere else in the visible sentence; the hint must NOT "
            f"contain the answer; give a natural English translation. Do not repeat "
            f"the example sentences."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Grammar point: {point.get('title')}\n"
                f"Explanation: {point.get('explanation') or '(none)'}\n"
                f"Existing drills (do not repeat):\n{examples or '  (none)'}"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _DRILL_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        return json.loads(text).get("drills", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _leaks(sentence: str, answer: str) -> bool:
    """The answer appears in the VISIBLE sentence (blank blanked out) — it would
    give itself away. Mirrors the edit_drill guard."""
    visible = sentence.replace("{{answer}}", " ")
    return bool(
        re.search(rf"(?<![^\W\d_]){re.escape(answer)}(?![^\W\d_])", visible, re.IGNORECASE)
    )


async def check_drill(language_code: str, cand: dict) -> tuple[bool, str]:
    """Verify one candidate against the same bar a human edit must clear.
    Returns (accepted, reason)."""
    sentence = (cand.get("sentence") or "").strip()
    answer = (cand.get("answer") or "").strip()
    hint = (cand.get("hint") or "").strip()
    if not sentence or not answer:
        return False, "missing sentence or answer"
    if " " in answer:
        return False, "answer is not a single token"
    if _leaks(sentence, answer):
        return False, "answer leaks into the visible sentence"
    if hint and answer.lower() in hint.lower():
        return False, "hint reveals the answer"
    if not await validate_drill(language_code, sentence, answer):
        return False, "failed the NLP answerability gate"
    return True, "ok"


async def check_drills(language_code: str, candidates: list[dict]) -> list[dict]:
    """Run every candidate through the checker. Returns each tagged with an
    `accepted` bool and a `reason` (kept for reporting/telemetry)."""
    out = []
    for cand in candidates:
        accepted, reason = await check_drill(language_code, cand)
        out.append({**cand, "accepted": accepted, "reason": reason})
    return out


async def generate_drills(
    point: dict,
    n: int,
    language: str,
    language_code: str,
    maker_model: str | None = None,
) -> list[dict]:
    """Maker then checker. Returns the candidates that PASSED, each carrying its
    verdict; the caller persists them (source='ai')."""
    made = await make_drills(point, n, language, maker_model)
    checked = await check_drills(language_code, made)
    return [c for c in checked if c["accepted"]]


# ---------------------------------------------------------------------------
# Vocabulary EXAMPLE sentences (same maker–checker shape as the drills above).
#
# Where a drill teaches a grammar FORM, a vocab example simply has to USE the
# target word naturally — so the checker's core gate is word-presence: the
# generated sentence must actually contain an inflected form of the word.
# Prefer the language's NLP backend (lemmatize each token); fall back to a
# whole-word surface match for languages with no backend — the low-density
# case this feature most serves (owner: "maker checker for the low density
# languages … where sentences … are saved and ingested").
# ---------------------------------------------------------------------------

_EXAMPLE_SCHEMA = {
    "type": "object",
    "properties": {
        "examples": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "sentence": {
                        "type": "string",
                        "description": "A natural sentence in the target "
                        "language that USES the target word.",
                    },
                    "translation": {"type": "string"},
                },
                "required": ["sentence", "translation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["examples"],
    "additionalProperties": False,
}

# A usable example is a real sentence, not a fragment or a wall of text.
MIN_EXAMPLE_LEN = 6
MAX_EXAMPLE_LEN = 240


def _mock_examples(word: dict, n: int) -> list[dict]:
    """Deterministic candidates for dev/testing. The first deliberately OMITS
    the target word (fails the word-presence gate) so the reject path is
    exercised, mirroring _mock_drills."""
    surface = (word.get("word") or "palabra").strip()
    out = [{
        "sentence": "This filler sentence never uses the target at all.",
        "translation": "Filler with no target word.",
    }]
    for i in range(1, n):
        out.append({
            "sentence": f"Aquí está {surface} en la oración {i}.",
            "translation": f"Here is the word in sentence {i}.",
        })
    return out[:n]


async def make_examples(
    word: dict, n: int, language: str, model: str | None = None
) -> list[dict]:
    """Draft N candidate example sentences that use a vocabulary word.

    *word*: {word, part_of_speech, definition, examples: [existing sentences]}.
    Returns raw candidates (unverified) — always run check_examples() first.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_examples(word, n)
    existing = "\n".join(f"  - {s}" for s in (word.get("examples") or [])[:6])
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("sentence_maker", language),
        max_tokens=2048,
        system=(
            f"You write natural example sentences in {language} for a vocabulary "
            f"flashcard app. Produce {n} NEW sentences that each USE the target "
            f'word "{word.get("word")}" ({word.get("part_of_speech") or "word"}, '
            f'meaning: {word.get("definition") or "n/a"}). Rules, strictly: every '
            f"sentence must actually contain the target word (any correct "
            f"inflection is fine); keep each natural, everyday, and unambiguous; "
            f"vary the context; give a natural English translation. Do not repeat "
            f"the existing examples."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Target word: {word.get('word')}\n"
                f"Part of speech: {word.get('part_of_speech') or '(unknown)'}\n"
                f"Meaning: {word.get('definition') or '(none)'}\n"
                f"Existing examples (do not repeat):\n{existing or '  (none)'}"
            ),
        }],
        output_config={"format": {"type": "json_schema", "schema": _EXAMPLE_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        return json.loads(text).get("examples", [])
    except (json.JSONDecodeError, TypeError):
        return []


def _contains_word(language_code: str, sentence: str, lemma: str) -> bool:
    """The generated sentence actually USES the target word — the core
    correctness gate for a vocab example. Whole-word surface match first (cheap,
    and all a backend-less low-density language gets); then, if a backend is
    registered, lemmatize each token / check the morphological family so an
    inflected form still counts."""
    lemma_n = (lemma or "").strip().lower()
    if not lemma_n:
        return False
    tokens = re.findall(r"[^\W\d_]+", sentence or "", re.UNICODE)
    lower_tokens = {t.lower() for t in tokens}
    if lemma_n in lower_tokens:
        return True
    try:
        nlp = get_nlp(language_code)
    except Exception:
        return False  # no backend: surface match was the only chance
    for tok in tokens:
        try:
            if nlp.lemmatize(tok).lower() == lemma_n:
                return True
        except Exception:
            continue
    try:
        family = {w.lower() for w in nlp.get_morphological_family(lemma_n)}
        if family & lower_tokens:
            return True
    except Exception:
        pass
    return False


async def check_example(
    language_code: str, cand: dict, lemma: str
) -> tuple[bool, str]:
    """Verify one candidate example. Returns (accepted, reason)."""
    sentence = (cand.get("sentence") or "").strip()
    translation = (cand.get("translation") or "").strip()
    if not sentence:
        return False, "missing sentence"
    if not translation:
        return False, "missing translation"
    if not (MIN_EXAMPLE_LEN <= len(sentence) <= MAX_EXAMPLE_LEN):
        return False, "sentence length out of range"
    if not _contains_word(language_code, sentence, lemma):
        return False, "sentence does not use the target word"
    return True, "ok"


async def check_examples(
    language_code: str, candidates: list[dict], lemma: str
) -> list[dict]:
    """Run every candidate through check_example, tagging accepted/reason."""
    out = []
    for cand in candidates:
        accepted, reason = await check_example(language_code, cand, lemma)
        out.append({**cand, "accepted": accepted, "reason": reason})
    return out


async def generate_examples(
    word: dict,
    n: int,
    language: str,
    language_code: str,
    maker_model: str | None = None,
) -> list[dict]:
    """Maker then checker for vocab example sentences. Returns the candidates
    that PASSED; the caller persists them (source='ai')."""
    lemma = word.get("lemma") or word.get("word") or ""
    made = await make_examples(word, n, language, maker_model)
    checked = await check_examples(language_code, made, lemma)
    return [c for c in checked if c["accepted"]]
