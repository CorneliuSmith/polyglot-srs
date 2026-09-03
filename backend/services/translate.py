"""Maker–checker translation of English course content into a support locale.

A learner studying English *from* their language sees the gloss in that
language. Many locales are thin or empty. This fills them with a two-pass AI:

  Maker   — generates the L1 gloss for a batch of English words, given each
            word's English definition, part of speech, and a real example so
            it picks the RIGHT sense (not "a → bishop").
  Checker — grades each maker gloss against the English sense and, when it
            can, returns a corrected final. Verdict drives the gate:
              ok / fixed  → apply the final gloss
              reject      → queue it for a human, never auto-apply.

Both passes are batched (many words per call) to keep the run affordable, and
use structured JSON output. Mock mode (TUTOR_DEV_MOCK) returns deterministic
stubs so the pipeline is testable with no API key.
"""
from __future__ import annotations

import json

from anthropic import AsyncAnthropic

from backend.config import get_settings
from backend.services.models import resolve_model
from backend.services.translate_checks import gate

_MAKER_SCHEMA = {
    "type": "object",
    "properties": {
        "glosses": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "gloss": {"type": "string",
                              "description": "The word/short phrase a native "
                              "speaker of the target language would use for THIS "
                              "sense. No English, no notes."},
                },
                "required": ["i", "gloss"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["glosses"],
    "additionalProperties": False,
}

_CHECKER_SCHEMA = {
    "type": "object",
    "properties": {
        "verdicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "verdict": {"type": "string", "enum": ["ok", "fixed", "reject"]},
                    "final": {"type": "string",
                              "description": "The gloss to store: unchanged when "
                              "ok, corrected when fixed, empty when reject."},
                    "note": {"type": "string",
                             "description": "Why, when fixed or reject. Empty otherwise."},
                },
                "required": ["i", "verdict", "final", "note"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["verdicts"],
    "additionalProperties": False,
}


def translations_available() -> bool:
    settings = get_settings()
    return bool(settings.anthropic_api_key) or getattr(settings, "tutor_dev_mock", False)


def _client() -> AsyncAnthropic:
    return AsyncAnthropic(api_key=get_settings().anthropic_api_key)


def maker_system(target_language: str, source_language: str = "English") -> str:
    """The maker's charter. Byte-identical to the original English-course
    prompt when source_language is English; for any other course the English
    definition stays the sense-disambiguator (the pivot), so the wording
    names both languages explicitly."""
    disambiguator = (
        "the definition and example" if source_language == "English"
        else "the English definition and example"
    )
    return (
        f"You are a professional lexicographer translating {source_language} "
        f"headwords into {target_language} for a language-learning app. For each "
        f"numbered {source_language} word, give the single word or short phrase a "
        f"native {target_language} speaker would use for THAT specific sense "
        f"(use {disambiguator} to disambiguate). Match the part of "
        f"speech. Output {target_language} only — no English, no explanations."
    )


def checker_system(target_language: str, source_language: str = "English") -> str:
    """The checker's charter, generalized the same way as maker_system."""
    return (
        f"You are a strict bilingual reviewer checking "
        f"{source_language}→{target_language} "
        f"glosses for a learner app. For each item decide: 'ok' if the gloss is "
        f"the correct sense, natural, and right part of speech; 'fixed' if it is "
        f"close but you can correct it (put the correction in final); 'reject' if "
        f"it is wrong-sense, unnatural, or you are unsure (final empty). Be "
        f"conservative — reject rather than guess."
    )


def sentence_checker_system(target_language: str) -> str:
    """The checker charter for FULL SENTENCES. Sentences were graded with the
    word-gloss charter ("right part of speech") for want of their own; this
    one names the failure classes the program has actually caught:

    * output not in the target language at all — a Spanish learner was once
      shown Greek and Romanian under "TRADUCCIÓN", because the script-based
      locale guard is silent between Latin alphabets;
    * English left untranslated beyond genuinely quoted course material;
    * meaning drift — a dropped negation, a changed subject, a hedged claim
      turned flat;
    * the locale's own conventions: Spanish questions and exclamations open
      with ¿ and ¡."""
    return (
        f"You are a strict reviewer of English→{target_language} sentence "
        f"translations for a learner app. For each item decide: 'ok' if the "
        f"rendering is fully in {target_language}, faithful (no dropped "
        f"negation, no changed subject, no added or lost meaning), natural, "
        f"and follows {target_language} orthography and punctuation "
        f"conventions; 'fixed' if it is close and you can correct it (put "
        f"the corrected sentence in final); 'reject' if it is in the wrong "
        f"language, part-translated, unfaithful, or you are unsure (final "
        f"empty). Quoted course-language material may stay untranslated; "
        f"everything else must read as native {target_language}. Be "
        f"conservative — reject rather than guess."
    )


def _mock_glosses(items: list[dict]) -> list[dict]:
    # deterministic stub: echo the English word tagged, so tests can assert flow
    return [{"i": it["i"], "gloss": f"[{it['word']}]"} for it in items]


def _mock_verdicts(items: list[dict]) -> list[dict]:
    # first item of every batch is rejected so the queue path is exercised
    out = []
    for n, it in enumerate(items):
        if n == 0:
            out.append({"i": it["i"], "verdict": "reject", "final": "",
                        "note": "[dev mock] flagged for review"})
        else:
            out.append({"i": it["i"], "verdict": "ok", "final": it["gloss"], "note": ""})
    return out


async def make_glosses(target_language: str, items: list[dict],
                       model: str | None = None, *,
                       source_language: str = "English") -> dict[int, str]:
    """Maker: {i -> gloss} for each item {i, word, definition, pos, example}.

    *source_language* is the language the headwords are in. The default,
    English, is the original English-course path; the auto-translate loop
    passes the course language (e.g. "Spanish") and the pivot rule applies:
    the English definition/example disambiguate which sense to render.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {g["i"]: g["gloss"] for g in _mock_glosses(items)}
    lines = "\n".join(
        f'{it["i"]}. "{it["word"]}" ({it.get("pos") or "?"}) — {it.get("definition") or ""}'
        + (f'  e.g. {it["example"]}' if it.get("example") else "")
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=maker_system(target_language, source_language),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _MAKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {g["i"]: (g.get("gloss") or "").strip()
            for g in data.get("glosses", []) if (g.get("gloss") or "").strip()}


async def check_glosses(target_language: str, items: list[dict],
                        model: str | None = None, *,
                        source_language: str = "English",
                        system: str | None = None) -> dict[int, dict]:
    """Checker: {i -> {verdict, final, note}} for items {i, word, definition, gloss}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {v["i"]: v for v in _mock_verdicts(items)}
    lines = "\n".join(
        f'{it["i"]}. {source_language} "{it["word"]}" '
        f'(English definition: {it.get("definition") or ""}) '
        f'→ proposed {target_language}: "{it["gloss"]}"'
        for it in items
    )
    resp = await _client().messages.create(
        # One tier up from the maker (models.py: never self-certify). Every
        # caller that reuses this checker — the sentence and UI-text lanes
        # pass their own `system` — inherits the floor.
        model=model or resolve_model("translate_checker"),
        max_tokens=4096,
        system=system or checker_system(target_language, source_language),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _CHECKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    out = {}
    for v in data.get("verdicts", []):
        verdict = v.get("verdict")
        if verdict not in ("ok", "fixed", "reject"):
            verdict = "reject"
        out[v["i"]] = {"verdict": verdict, "final": (v.get("final") or "").strip(),
                       "note": (v.get("note") or "").strip()}
    return out


async def maker_check_batch(target_language: str, items: list[dict],
                            maker_model: str | None = None,
                            checker_model: str | None = None, *,
                            source_language: str = "English") -> list[dict]:
    """Run maker then checker over a batch. Returns per-item results:
    {i, word, gloss, proposed, verdict, note}.

    `gloss` is what to STORE — empty when the checker rejected. `proposed`
    is what the maker actually wrote, kept even on a reject, because the
    review queue exists precisely to show a human the rejected proposal.
    Dropping it left every row in that queue with nothing to approve: the
    reviewer saw a word, a reason, and a Reject button, which is not a
    review, it is a bin.
    """
    made = await make_glosses(target_language, items, maker_model,
                              source_language=source_language)
    checkable = [
        {**it, "gloss": made[it["i"]]} for it in items if it["i"] in made
    ]
    if not checkable:
        return []
    verdicts = await check_glosses(target_language, checkable, checker_model,
                                   source_language=source_language)
    results = []
    for it in checkable:
        v = verdicts.get(it["i"], {"verdict": "reject", "final": "", "note": "no verdict"})
        store = it["gloss"] if v["verdict"] == "ok" else v["final"]
        results.append({
            "i": it["i"], "word": it["word"],
            "gloss": store if v["verdict"] in ("ok", "fixed") else "",
            # The checker's correction if it offered one, else the maker's
            # own attempt — either way, something a reviewer can judge.
            "proposed": (v.get("final") or "").strip() or it["gloss"],
            "verdict": v["verdict"], "note": v["note"],
        })
    return results


_SENTENCE_MAKER_SCHEMA = {
    "type": "object",
    "properties": {
        "translations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "i": {"type": "integer"},
                    "translation": {"type": "string",
                                    "description": "The full sentence rendered "
                                    "naturally in the target language."},
                },
                "required": ["i", "translation"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["translations"],
    "additionalProperties": False,
}


def _mock_sentence_translations(items: list[dict], target_language: str) -> list[dict]:
    return [{"i": it["i"], "translation": f"[{target_language}] {it['sentence']}"}
            for it in items]


async def make_sentence_translations(
    target_language: str, items: list[dict], model: str | None = None,
) -> dict[int, str]:
    """Maker: {i -> translation} of each English sentence into *target_language*.
    items: {i, sentence}."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {t["i"]: t["translation"]
                for t in _mock_sentence_translations(items, target_language)}
    lines = "\n".join(f'{it["i"]}. {it["sentence"]}' for it in items)
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You translate English example sentences into {target_language} for "
            f"a learner app. For each numbered sentence give a natural, faithful "
            f"{target_language} translation. If a word or idiom has no direct "
            f"equivalent, render the meaning naturally in {target_language} rather "
            f"than translating literally; only keep an English term if that is "
            f"genuinely how {target_language} speakers say it. Output "
            f"{target_language} only."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _SENTENCE_MAKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {t["i"]: (t.get("translation") or "").strip()
            for t in data.get("translations", []) if (t.get("translation") or "").strip()}


async def generate_sentence_translations(
    target_language: str, items: list[dict],
    maker_model: str | None = None, checker_model: str | None = None,
    *, locale: str = "",
) -> list[dict]:
    """Maker then checker then MECHANICAL GATES: translate English sentences
    into a support locale. items: {i, sentence, answer?}. Returns
    {i, sentence, translation, proposed, verdict, note}; translation is the
    final to store (empty when rejected). `proposed` is the rendering a human
    would judge — the checker's correction if it offered one, else the
    maker's own — kept on a reject so the review queue has something to
    approve (the same lesson maker_check_batch learned for glosses).

    The gates (translate_checks.gate) run on every rendering, mock mode
    included, so the tests exercise them without a model: a rendering that
    contains the item's cloze `answer`, echoes its source, alters a blank, or
    drops the locale's inverted punctuation is withheld — the row stays
    unfilled and a later sweep retries, instead of a defect landing behind
    COALESCE where nothing re-examines it."""
    made = await make_sentence_translations(target_language, items, maker_model)
    by_i = {it["i"]: it for it in items}
    checkable = [
        {"i": it["i"], "word": it["sentence"], "sentence": it["sentence"],
         "definition": "", "gloss": made[it["i"]]}
        for it in items if it["i"] in made
    ]
    if not checkable:
        return []
    verdicts = await check_glosses(
        target_language, checkable, checker_model,
        system=sentence_checker_system(target_language))
    results = []
    for it in checkable:
        v = verdicts.get(it["i"], {"verdict": "reject", "final": "", "note": "no verdict"})
        store = it["gloss"] if v["verdict"] == "ok" else v["final"]
        verdict, note = v["verdict"], v["note"]
        if verdict in ("ok", "fixed") and store:
            reason = gate(it["sentence"], store, locale=locale,
                          answer=(by_i.get(it["i"], {}).get("answer") or ""))
            if reason:
                verdict, note, store = "reject", f"gate: {reason}", ""
        results.append({
            "i": it["i"], "sentence": it["sentence"],
            "translation": store if verdict in ("ok", "fixed") else "",
            "proposed": (v.get("final") or "").strip() or it["gloss"],
            "verdict": verdict, "note": note,
        })
    return results


_TEXT_SYSTEMS = {
    # Short UI strings: grammar-point titles, Gym form labels and their
    # one-line usage notes. The rule that matters: text already in the
    # course language (endings like "-ar", articles like "(el / la)",
    # example words) is quoted material, not English to translate.
    "label": (
        "You translate short English labels from a language-learning app into "
        "{target}: grammar-point titles, form-category names, and one-line "
        "usage notes about a course language. Keep them as short and plain as "
        "the original. Anything that is course-language material rather than "
        "English — verb endings like -ar, quoted words, bracketed forms like "
        "(el / la) — must be copied unchanged. Use the grammatical terms a "
        "{target}-speaking learner would meet in a textbook. Output {target} "
        "only."
    ),
    # Prose: grammar explanations, culture notes, function notes.
    "prose": (
        "You translate short English explanations from a language-learning "
        "app into {target}: grammar lessons, culture notes and usage notes "
        "about a course language. Render the meaning in natural {target} at "
        "the same length and register — plain, friendly, precise. Course-"
        "language material inside the text (example words, endings, quoted "
        "phrases) must be copied unchanged; grammatical terms should be the "
        "ones a {target}-speaking learner would meet in a textbook. Output "
        "{target} only."
    ),
}


async def make_text_translations(
    target_language: str, items: list[dict], kind: str = "prose",
    model: str | None = None,
) -> dict[int, str]:
    """Maker: {i -> translation} of each English text into *target_language*
    with a purpose-fit charter. items: {i, sentence}; kind: 'label'|'prose'."""
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return {t["i"]: t["translation"]
                for t in _mock_sentence_translations(items, target_language)}
    lines = "\n".join(f'{it["i"]}. {it["sentence"]}' for it in items)
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=_TEXT_SYSTEMS[kind].format(target=target_language),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _SENTENCE_MAKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}
    return {t["i"]: (t.get("translation") or "").strip()
            for t in data.get("translations", []) if (t.get("translation") or "").strip()}


async def generate_text_translations(
    target_language: str, items: list[dict], kind: str = "prose",
    maker_model: str | None = None, checker_model: str | None = None,
    *, locale: str = "",
) -> list[dict]:
    """Maker then checker then the same mechanical gates as sentences, for
    non-sentence texts (titles, labels, notes, explanations). items may carry
    `answer` — a drill HINT translated here must never contain the answer the
    drill asks for, and the label charter's own (correct) instruction to copy
    quoted course-language material unchanged is exactly how an English hint
    that quotes its answer would carry the leak into every locale."""
    made = await make_text_translations(target_language, items, kind, maker_model)
    by_i = {it["i"]: it for it in items}
    checkable = [
        {"i": it["i"], "word": it["sentence"], "sentence": it["sentence"],
         "definition": "", "gloss": made[it["i"]]}
        for it in items if it["i"] in made
    ]
    if not checkable:
        return []
    verdicts = await check_glosses(target_language, checkable, checker_model)
    results = []
    for it in checkable:
        v = verdicts.get(it["i"], {"verdict": "reject", "final": "", "note": "no verdict"})
        store = it["gloss"] if v["verdict"] == "ok" else v["final"]
        verdict, note = v["verdict"], v["note"]
        if verdict in ("ok", "fixed") and store:
            reason = gate(it["sentence"], store, locale=locale,
                          answer=(by_i.get(it["i"], {}).get("answer") or ""))
            if reason:
                verdict, note, store = "reject", f"gate: {reason}", ""
        results.append({
            "i": it["i"], "sentence": it["sentence"],
            "translation": store if verdict in ("ok", "fixed") else "",
            "proposed": (v.get("final") or "").strip() or it["gloss"],
            "verdict": verdict, "note": note,
        })
    return results


async def review_definitions(target_language: str, items: list[dict],
                             model: str | None = None) -> list[dict]:
    """Clarity pass over EXISTING card definitions/hints (not a translation).

    Catches misleading wording — e.g. a Russian imperfective glossed
    "to speak, to talk (perfective поговорить)", which reads like it wants the
    perfective. items: {i, word, definition}. Returns per item
    {i, word, verdict, definition, note}: 'ok' keep as-is, 'fixed' use the
    reworded `definition`, 'reject' → empty (queue for a human).
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return [{"i": it["i"], "word": it["word"],
                 "verdict": "ok", "definition": it["definition"], "note": ""}
                for it in items]
    lines = "\n".join(
        f'{it["i"]}. "{it["word"]}" — {it["definition"]}' for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You review flash-card definitions for learners of {target_language}. "
            "For each, judge CLARITY, not translation: is it unambiguous and not "
            "misleading? A common fault is a parenthetical that reads like an "
            "instruction — e.g. an imperfective verb glossed '...(perfective X)' "
            "looks like it's asking for X. Verdict 'ok' if it's clear; 'fixed' if "
            "you can reword it clearly (keep the meaning, put any partner/aspect "
            "note in plain words, e.g. 'to speak (imperfective; pairs with X)') and "
            "put it in `final`; 'reject' if you're unsure. Keep it concise."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _CHECKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    by_i = {}
    for v in data.get("verdicts", []):
        verdict = v.get("verdict")
        if verdict not in ("ok", "fixed", "reject"):
            verdict = "reject"
        by_i[v["i"]] = (verdict, (v.get("final") or "").strip(), (v.get("note") or "").strip())
    out = []
    for it in items:
        verdict, final, note = by_i.get(it["i"], ("reject", "", "no verdict"))
        definition = it["definition"] if verdict == "ok" else final
        out.append({"i": it["i"], "word": it["word"], "verdict": verdict,
                    "definition": definition if verdict in ("ok", "fixed") else "",
                    "note": note})
    return out


_TRIVIA_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "options": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3, "maxItems": 4,
                    },
                    "answer_index": {"type": "integer"},
                    "fact": {
                        "type": "string",
                        "description": "One sentence of payoff shown after "
                                       "answering — the part worth remembering.",
                    },
                },
                "required": ["question", "options", "answer_index", "fact"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["questions"],
    "additionalProperties": False,
}

_TRIVIA_SYSTEM = """You write short multiple-choice trivia about human \
language: writing systems, etymology, language families, sounds, grammar \
across languages, how many people speak what, and the odd surprising fact.

Write ENTIRELY in {target}. Every question, every option and the fact must \
be in {target} — this is read by someone who chose {target} as the language \
they are comfortable in.

Rules:
- Exactly one option is correct, and answer_index points at it (0-based).
- Wrong options must be plausible, not filler. No "none of the above".
- Keep questions to one sentence. Assume no linguistics training.
- The fact is ONE sentence that pays off the question with something worth \
knowing, not a restatement of the answer.
- Be accurate. If you are unsure of a figure, ask something you are sure of \
instead. A wrong fact is worse than a dull one.
- Do NOT ask about any of the questions listed as already asked."""


async def generate_trivia(
    target_language: str, count: int, avoid: list[str] | None = None,
    model: str | None = None,
) -> list[dict]:
    """A batch of language-trivia questions written in *target_language*.

    *avoid* carries questions already in the bank so the corpus grows rather
    than circling the same handful. Returns [] on anything unexpected — this
    feeds a waiting-room game, and no game is better than a broken one.
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return [
            {"question": f"[{target_language}] Q{i}",
             "options": [f"A{i}", f"B{i}", f"C{i}"],
             "answer_index": i % 3,
             "fact": f"[{target_language}] fact {i}"}
            for i in range(count)
        ]
    avoid_block = ""
    if avoid:
        joined = "\n".join(f"- {q}" for q in avoid[:80])
        avoid_block = f"\n\nAlready asked, do not repeat:\n{joined}"
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=_TRIVIA_SYSTEM.format(target=target_language),
        messages=[{
            "role": "user",
            "content": f"Write {count} questions.{avoid_block}",
        }],
        output_config={"format": {"type": "json_schema", "schema": _TRIVIA_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    out = []
    for q in data.get("questions", []):
        opts = [str(o).strip() for o in q.get("options", []) if str(o).strip()]
        idx = q.get("answer_index")
        # A question whose answer index doesn't point at a real option is
        # unanswerable; drop it rather than storing a broken row.
        if (len(opts) < 2 or not isinstance(idx, int)
                or not 0 <= idx < len(opts)
                or not (q.get("question") or "").strip()
                or not (q.get("fact") or "").strip()):
            continue
        out.append({
            "question": q["question"].strip(),
            "options": opts,
            "answer_index": idx,
            "fact": q["fact"].strip(),
        })
    return out


async def review_source_translations(
    source_language: str, items: list[dict], model: str | None = None,
) -> list[dict]:
    """Judge the ENGLISH against the sentence it claims to translate.

    Every other checker here runs English → L: the English is treated as
    ground truth and each locale is generated from it. Nothing ever asked
    whether the English itself is faithful, so a loose rendering silently
    caps every language derived from it — the owner noticed a Spanish
    translation that was fine while the English it came from was not.

    Direction is therefore reversed: *sentence* is in the language being
    taught, *translation* is the English under review.

    items: {i, sentence, translation}. Returns {i, verdict, translation,
    note}: 'ok' keep, 'fixed' use the corrected English, 'reject' → empty
    (a human decides, via the review queue).
    """
    settings = get_settings()
    if getattr(settings, "tutor_dev_mock", False):
        return [{"i": it["i"], "verdict": "ok",
                 "translation": it["translation"], "note": ""} for it in items]
    lines = "\n".join(
        f'{it["i"]}. {source_language}: {it["sentence"]}\n   English: {it["translation"]}'
        for it in items
    )
    resp = await _client().messages.create(
        model=model or resolve_model("translate"),
        max_tokens=4096,
        system=(
            f"You check English translations of {source_language} sentences for a "
            "language course. The English is what learners read to understand the "
            f"{source_language}, and every other language's version is generated "
            "FROM this English — so an imprecise English silently corrupts every "
            "other locale.\n"
            "Judge only the ENGLISH. Verdict 'ok' when it is accurate and natural. "
            "'fixed' when you can do better, putting the replacement in `final`: "
            "correct meaning errors, wrong register, and renderings that are "
            "defensible but misleading out of context. Prefer the natural English a "
            "speaker would actually say over a word-by-word gloss, but do not drift "
            "further from the source than the original did. Keep it the same kind of "
            "utterance — a question stays a question, a fragment stays a fragment. "
            "'reject' when the pair is too broken or ambiguous to fix confidently "
            "(e.g. the English translates a different sentence).\n"
            "Say in `note` what was wrong, in a few words. Leave `note` empty for 'ok'."
        ),
        messages=[{"role": "user", "content": lines}],
        output_config={"format": {"type": "json_schema", "schema": _CHECKER_SCHEMA}},
    )
    text = next((b.text for b in resp.content if b.type == "text"), "{}")
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return []
    by_i = {}
    for v in data.get("verdicts", []):
        verdict = v.get("verdict")
        if verdict not in ("ok", "fixed", "reject"):
            verdict = "reject"
        by_i[v["i"]] = (verdict, (v.get("final") or "").strip(),
                        (v.get("note") or "").strip())
    out = []
    for it in items:
        verdict, final, note = by_i.get(it["i"], ("reject", "", "no verdict"))
        # A 'fixed' that came back identical is really an 'ok'; storing it
        # would spend a write and a stale-marking for nothing.
        if verdict == "fixed" and final == it["translation"]:
            verdict, note = "ok", ""
        out.append({
            "i": it["i"], "verdict": verdict,
            "translation": (it["translation"] if verdict == "ok"
                            else final if verdict == "fixed" else ""),
            "note": note,
        })
    return out
