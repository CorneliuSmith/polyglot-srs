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
from backend.services.apertium import analyze_lemmas, apertium_available
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
    point: dict, n: int, language: str, model: str | None = None,
    cell: str | None = None,
) -> list[dict]:
    """Draft N candidate drills for a grammar point.

    *point*: {title, explanation, examples: [existing drill sentences]}.
    *cell*: when set, every drill must exercise THAT paradigm cell (e.g. the
    "vosotros" form) so thickening stays balanced instead of piling on one cell.
    Returns raw candidate dicts (unverified) — always run them through
    check_drills() before storing.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_drills(point, n)
    examples = "\n".join(f"  - {s}" for s in (point.get("examples") or [])[:6])
    cell_rule = (
        f" EVERY drill must exercise the '{cell}' form specifically." if cell else ""
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("grammar_maker", language),
        max_tokens=2048,
        system=(
            f"You author fill-in-the-blank grammar drills in {language} for a "
            f"spaced-repetition app. Produce {n} NEW drills for the grammar point "
            f'"{point.get("title")}".{cell_rule} Vary the vocabulary and sentence '
            f"frame; keep each natural and unambiguous. Rules, strictly: the "
            f"sentence contains the literal token {{{{answer}}}} exactly once where "
            f"the target form goes; the answer is a SINGLE word/word-form; the "
            f"answer must NOT appear anywhere else in the visible sentence; the "
            f"hint must NOT contain the answer; give a natural English translation. "
            f"Do not repeat the example sentences."
        ),
        messages=[{
            "role": "user",
            "content": (
                f"Grammar point: {point.get('title')}\n"
                f"Explanation: {point.get('explanation') or '(none)'}\n"
                + (f"Target form (cell): {cell}\n" if cell else "")
                + f"Existing drills (do not repeat):\n{examples or '  (none)'}"
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
    cell: str | None = None,
) -> list[dict]:
    """Maker then checker. Returns the candidates that PASSED, each carrying its
    verdict; the caller persists them (source='ai'). When *cell* is set, the
    drills all exercise that paradigm cell (balanced thickening)."""
    made = await make_drills(point, n, language, maker_model, cell=cell)
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


def _is_english(language_code: str | None) -> bool:
    """English is the app's support locale (WP: support_locale='en'). A literal
    English→English translation is redundant, so for English content the
    `translation` field carries a plain-English DESCRIPTION (a simpler
    restatement) instead — a comprehension aid rather than an echo."""
    return (language_code or "").split("-")[0].lower() == "en"


def _translation_rule(language_code: str | None) -> str:
    """What to put in a sentence's `translation` field, per target language."""
    if _is_english(language_code):
        return (
            "give a short, simpler plain-English DESCRIPTION of the sentence "
            "(a restatement in easier words — NOT a word-for-word copy)"
        )
    return "give a natural English translation"


def _mock_examples(word: dict, n: int, language_code: str | None = None) -> list[dict]:
    """Deterministic candidates for dev/testing. The first deliberately OMITS
    the target word (fails the word-presence gate) so the reject path is
    exercised, mirroring _mock_drills."""
    surface = (word.get("word") or "palabra").strip()
    gloss = "In simpler words" if _is_english(language_code) else "Here is the word"
    out = [{
        "sentence": "This filler sentence never uses the target at all.",
        "translation": "Filler with no target word.",
    }]
    for i in range(1, n):
        out.append({
            "sentence": f"Aquí está {surface} en la oración {i}.",
            "translation": f"{gloss} in sentence {i}.",
        })
    return out[:n]


async def make_examples(
    word: dict, n: int, language: str, language_code: str | None = None,
    model: str | None = None,
) -> list[dict]:
    """Draft N candidate example sentences that use a vocabulary word.

    *word*: {word, part_of_speech, definition, examples: [existing sentences]}.
    Returns raw candidates (unverified) — always run check_examples() first.
    For English (*language_code* 'en') the translation is a plain-English
    description, since an English→English translation would be redundant.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_examples(word, n, language_code)
    existing = "\n".join(f"  - {s}" for s in (word.get("examples") or [])[:6])
    level = (word.get("level") or "").strip()
    level_rule = (
        f" Pitch them for a CEFR {level} learner." if level else ""
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("sentence_maker", language),
        max_tokens=2048,
        system=(
            f"You write natural example sentences in {language} for a vocabulary "
            f"flashcard app. Produce {n} NEW sentences that each USE the target "
            f'word "{word.get("word")}" ({word.get("part_of_speech") or "word"}, '
            f'meaning: {word.get("definition") or "n/a"}).{level_rule} Rules, '
            f"strictly: every sentence must actually contain the target word (any "
            f"correct inflection is fine); keep each natural, everyday, and "
            f"unambiguous; each must be genuinely USEFUL for a learner — a "
            f"complete, contextful sentence that shows how the word is really "
            f"used, NOT a trivial fragment, a bare label, or a stilted textbook "
            f"line; vary the context; {_translation_rule(language_code)}. Do not "
            f"repeat the existing examples."
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


async def _contains_word(language_code: str, sentence: str, lemma: str) -> bool:
    """The generated sentence actually USES the target word — the core
    correctness gate for a vocab example. In order of cost:
      1. whole-word surface match (cheap; all a backend-less language gets),
      2. the local NLP backend (lemmatize each token / morphological family) so
         an inflected form counts,
      3. failing (2) for a backend-less language, an optional Apertium call
         (WP42) — the opt-in way to still accept an inflected form there."""
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
        nlp = None
    if nlp is not None:
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
    # No local backend: ask Apertium if it's configured for this language. This
    # is what lets an inflected form count on a backend-less low-resource
    # language; unset/unsupported/errored -> empty set -> surface match stands.
    if apertium_available(language_code):
        return lemma_n in await analyze_lemmas(language_code, sentence)
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
    if not await _contains_word(language_code, sentence, lemma):
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
    made = await make_examples(word, n, language, language_code, maker_model)
    checked = await check_examples(language_code, made, lemma)
    return [c for c in checked if c["accepted"]]


# ---------------------------------------------------------------------------
# Quality AUDIT of EXISTING example sentences (the --recheck path).
#
# The mechanical checker above only gates NEW candidates; an existing sentence
# already contains its word, so a mechanical re-run would rarely reject one.
# To actually catch a sentence that is unnatural, ungrammatical, misuses the
# word, or is mistranslated, the audit runs an LLM judge (the 'sentence_checker'
# model, one tier up — §6: never self-certify) over a word's current sentences.
# The same call BACKFILLS a missing translation for any language (an English
# sentence with no translation gets a plain-English description). A sentence the
# judge rejects is FLAGGED for a human, never silently deleted.
# ---------------------------------------------------------------------------

_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The 0-based index of the sentence judged.",
                    },
                    "ok": {
                        "type": "boolean",
                        "description": "True if the sentence is natural, correct, "
                        "uses the target word, AND is complex/useful enough to "
                        "teach a learner something at its level. False for a "
                        "trivial, stilted, or low-value sentence.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Short reason when ok is false (say if it's "
                        "a correctness problem or a too-simple/low-value one); "
                        "empty when ok.",
                    },
                    "translation_ok": {
                        "type": "boolean",
                        "description": "True if the sentence's CURRENT translation "
                        "is present, accurate, and genuinely helpful to a learner. "
                        "False if it is missing, wrong, or unhelpful.",
                    },
                    "translation": {
                        "type": "string",
                        "description": "Your recommended translation/description "
                        "for the sentence. Used to fill a missing one, or as a "
                        "suggested replacement when translation_ok is false.",
                    },
                },
                "required": ["index", "ok", "reason", "translation_ok", "translation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def _mock_audit(sentences: list[dict], language_code: str | None) -> list[dict]:
    """Deterministic verdicts for dev/testing. A sentence containing 'bad' is
    rejected on correctness; one containing 'simple' is rejected as too
    trivial/low-value (the complexity flag). A missing translation is filled; a
    present one containing 'vague' is judged unhelpful and a replacement
    suggested. Lets a test drive every path from the sentence/translation text."""
    describe = _is_english(language_code)
    tr_label = "description" if describe else "translation"
    out = []
    for i, s in enumerate(sentences):
        text = (s.get("sentence") or "")
        low = text.lower()
        if "bad" in low:
            ok, reason = False, "flagged by quality audit"
        elif "simple" in low:
            ok, reason = False, "too simple to be useful for a learner"
        else:
            ok, reason = True, ""
        tr = (s.get("translation") or "").strip()
        tr_present = bool(tr)
        tr_weak = "vague" in tr.lower()
        translation_ok = tr_present and not tr_weak
        if not tr_present:
            rec = f"{'Description' if describe else 'Translation'}: {text[:60]}"
        elif tr_weak:
            rec = f"Clearer {tr_label}: {text[:60]}"
        else:
            rec = ""
        out.append({
            "index": i, "ok": ok, "reason": reason,
            "translation_ok": translation_ok, "translation": rec,
        })
    return out


async def audit_examples(
    word: dict,
    sentences: list[dict],
    language: str,
    language_code: str,
    model: str | None = None,
    level: str | None = None,
) -> list[dict]:
    """LLM quality judge over a word's EXISTING sentences.

    *sentences*: [{sentence, translation}] in order. *level*: the word's CEFR
    level, so "too simple" is judged relative to it. Returns a verdict per
    sentence, aligned by list position:
      {index, ok, reason, translation_ok, translation}
    `ok` covers correctness AND usefulness/complexity (a trivial or stilted
    sentence fails). `translation_ok` rates the CURRENT translation; `translation`
    is the recommended text — used to fill a missing one or as a suggested
    replacement for a weak one. Never mutates the DB — the caller acts on these.
    """
    if not sentences:
        return []
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_audit(sentences, language_code)

    listing = "\n".join(
        f"[{i}] sentence: {s.get('sentence') or ''}\n"
        f"    translation: {s.get('translation') or '(none)'}"
        for i, s in enumerate(sentences)
    )
    fill_rule = (
        "a short, simpler plain-English description of the sentence"
        if _is_english(language_code)
        else "a natural English translation"
    )
    level_rule = (
        f" The word's level is CEFR {level}; judge 'too simple' relative to it "
        f"(a bare label like \"It is 7:45.\" or a stilted line like \"It is I.\" "
        f"teaches little even to a beginner)." if (level or "").strip() else ""
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("sentence_checker", language),
        max_tokens=2048,
        system=(
            f"You are a strict reviewer of {language} example sentences for the "
            f'vocabulary word "{word.get("word")}" '
            f'(meaning: {word.get("definition") or "n/a"}). For EACH numbered '
            f"sentence, set ok=false (with a short reason) if it is unnatural, "
            f"ungrammatical, does not use the target word, OR is too trivial / "
            f"low-value to teach a learner anything useful.{level_rule} Separately, "
            f"rate its CURRENT translation: set translation_ok=false if the "
            f"translation is missing, inaccurate, or unhelpful. Always put your "
            f"recommended text in the translation field — for a missing one, "
            f"{fill_rule}; for a weak one, a clearer replacement; if the current "
            f"translation is already good, you may leave translation empty. "
            f"Return exactly one verdict per sentence, keyed by its [index]."
        ),
        messages=[{"role": "user", "content": listing}],
        output_config={"format": {"type": "json_schema", "schema": _AUDIT_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        verdicts = json.loads(text).get("verdicts", [])
    except (json.JSONDecodeError, TypeError):
        return []
    # Guard against a model that drops/reorders rows: index the response and
    # emit one verdict per input sentence in order, defaulting missing ones to
    # ok (never flag a sentence the judge didn't actually rule on).
    by_index = {v.get("index"): v for v in verdicts if isinstance(v, dict)}
    out = []
    for i in range(len(sentences)):
        v = by_index.get(i, {})
        out.append({
            "index": i,
            "ok": bool(v.get("ok", True)),
            "reason": (v.get("reason") or "").strip(),
            "translation_ok": bool(v.get("translation_ok", True)),
            "translation": (v.get("translation") or "").strip(),
        })
    return out


# ---------------------------------------------------------------------------
# Quality AUDIT of EXISTING drills (the --recheck path for grammar). Mirrors
# audit_examples: a judge rules each of a point's drills ok/not-ok; the caller
# FLAGS the rejects for a human and heals the point back to target with fresh
# generated alternatives. Drills are cloze sentences — the dimension is
# correctness + usefulness of the sentence, not a separate translation quality.
# ---------------------------------------------------------------------------

_DRILL_AUDIT_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "index": {
                        "type": "integer",
                        "description": "The 0-based index of the drill judged.",
                    },
                    "ok": {
                        "type": "boolean",
                        "description": "True if the drill is natural and correct, "
                        "the answer is the right form for its blank, AND it is "
                        "worth teaching. False for an ungrammatical, mis-keyed, or "
                        "trivially low-value drill.",
                    },
                    "reason": {
                        "type": "string",
                        "description": "Short reason when ok is false (name the "
                        "problem: wrong answer, unnatural sentence, or too simple); "
                        "empty when ok.",
                    },
                },
                "required": ["index", "ok", "reason"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def _mock_audit_drills(drills: list[dict]) -> list[dict]:
    """Deterministic verdicts for dev/testing, mirroring _mock_audit: a drill
    whose sentence contains 'bad' is rejected on correctness, 'simple' as too
    trivial; everything else passes. Lets a test drive both flag paths."""
    out = []
    for i, d in enumerate(drills):
        low = (d.get("sentence") or "").lower()
        if "bad" in low:
            ok, reason = False, "flagged by quality audit"
        elif "simple" in low:
            ok, reason = False, "too simple to teach the form"
        else:
            ok, reason = True, ""
        out.append({"index": i, "ok": ok, "reason": reason})
    return out


async def audit_drills(
    point: dict,
    drills: list[dict],
    language: str,
    language_code: str,
    model: str | None = None,
    level: str | None = None,
) -> list[dict]:
    """LLM quality judge over a grammar point's EXISTING drills.

    *drills*: [{sentence, answer, translation, hint}] in order. Returns a verdict
    per drill aligned by position: {index, ok, reason}. `ok` covers correctness
    (natural, right answer for the blank) AND usefulness (not trivial). Never
    mutates the DB — the caller flags the rejects and heals to target.
    """
    if not drills:
        return []
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return _mock_audit_drills(drills)

    listing = "\n".join(
        f"[{i}] sentence: {d.get('sentence') or ''}\n"
        f"    answer: {d.get('answer') or ''}"
        f"    translation: {d.get('translation') or '(none)'}"
        for i, d in enumerate(drills)
    )
    level_rule = (
        f" The point's level is CEFR {level}; judge 'too simple' relative to it."
        if (level or "").strip() else ""
    )
    client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    resp = await client.messages.create(
        model=model or resolve_model("sentence_checker", language),
        max_tokens=2048,
        system=(
            f"You are a strict reviewer of {language} fill-in-the-blank grammar "
            f'drills for the point "{point.get("title")}" '
            f'(explanation: {point.get("explanation") or "n/a"}). Each drill is a '
            f"sentence with a {{answer}} blank plus the expected answer. For EACH "
            f"numbered drill, set ok=false (with a short reason) if the sentence is "
            f"unnatural or ungrammatical, the answer is not the exactly correct "
            f"form for the blank, OR it is too trivial / low-value to teach the "
            f"form.{level_rule} Return exactly one verdict per drill, keyed by its "
            f"[index]."
        ),
        messages=[{"role": "user", "content": listing}],
        output_config={"format": {"type": "json_schema", "schema": _DRILL_AUDIT_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        verdicts = json.loads(text).get("verdicts", [])
    except (json.JSONDecodeError, TypeError):
        return []
    # Never flag a drill the judge didn't actually rule on: default missing → ok.
    by_index = {v.get("index"): v for v in verdicts if isinstance(v, dict)}
    out = []
    for i in range(len(drills)):
        v = by_index.get(i, {})
        out.append({
            "index": i,
            "ok": bool(v.get("ok", True)),
            "reason": (v.get("reason") or "").strip(),
        })
    return out
