"""Mechanical quality audit of the learning content committed to this repo.

Why this exists: three standing complaints — "Spanish hints give the answer
away", "Catalan has gender problems", "the Arabic may not be MSA" — were all
invisible to the test suite, because none of them had ever been *stated as a
rule*. Content could regress in every language and nothing would go red; the
only detector was a human reading drills one at a time. This module states the
mechanically checkable half of those standards and enforces it in CI.

What it does NOT do is judge meaning. Every rule here is a string operation
with a documented false-positive guard, because the guards are the whole
difficulty: the naive version of the leak check flags `trabajar, él/ella` for
answer `trabaja` (the legitimate "infinitive, person" convention) and the naive
Arabic dialect check flags المحلّفين ("jurors") as Egyptian فين, since a shadda
is not a word character and so reads as a word boundary. Rules that fire on
convention get ignored, and an ignored checker is worse than none.

Severities:
  * fail   — gated by data/quality/baseline.json. The audit exits 1 only when a
             count EXCEEDS its recorded baseline, so existing debt does not
             block anyone, but adding debt does.
  * warn   — reported, never gates.
  * report — a measurement with no pass/fail reading at all (gender marking).

Sub-classes are deliberately NOT exclusive: a self-answering hint is also a
hard leak and counts under both, because `self_answering` exists to name the
worst *pattern*, not to excuse it from the leak count.

Usage:
    python -m backend.services.quality.audit_content
    python -m backend.services.quality.audit_content --language ar
    python -m backend.services.quality.audit_content --language ca --sample 10
    python -m backend.services.quality.audit_content --update-baseline
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

# Single source of truth for the Arabic combining-mark ranges: the grader folds
# them the same way, and a checker that disagreed with the grader about what
# "the same word" means would flag content the app accepts.
from backend.services.nlp.arabic_script import _TASHKEEL as _ARABIC_MARKS

# backend/services/quality/audit_content.py -> repo root. Never absolutise this:
# the audit runs in CI, in the container, and on the owner's machine.
REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"
GRAMMAR_DIR = DATA / "grammar"
BASELINE_PATH = DATA / "quality" / "baseline.json"

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)

FAIL_RULES = (
    "leak_hard",
    "self_answering",
    "giveaway_by_gloss",
    "duplicate_hint",
    "empty",
    "ar_register",
)
WARN_RULES = ("construction_quote", "vague_translation", "hint_language", "structural")
# Measured and printed, never scored: "how often do noun hints mark gender" is
# a number to drive editorial work, not a threshold anyone can set honestly.
REPORT_RULES = ("gender_marking",)
ALL_RULES = FAIL_RULES + WARN_RULES + REPORT_RULES

# Languages whose learners need gender on every noun. `de` carries it as an
# Article chip (das/der/die) rather than a Gender chip.
GENDERED = frozenset("ca es fr it pt de nl el ru ar he ro".split())

# Target-script ranges for "the hint drifted into the target language". Latin
# script targets need a different test entirely (an English hint and a Spanish
# hint are the same characters), so they are absent by design.
# U+200C ZWNJ belongs inside the class: without it Persian نمی‌دانم splits into
# two tokens and trips the >=3 threshold on its own.
SCRIPT_RANGES = {
    "ru": "Ѐ-ӿ",
    "ar": "؀-ۿݐ-ݿ‌",
    "fa": "؀-ۿݐ-ݿ‌",
    "el": "Ͱ-Ͽἀ-῿",
    "hi": "ऀ-ॿ",
    "th": "฀-๿",
    "ko": "가-힯ᄀ-ᇿ㄰-㆏",
    "he": "֐-׿",
}

# Answers this short that are also English function words collide with English
# hint prose instead of leaking: every Spanish "personal a" hit was the article
# in "a person", not the answer being given away.
ENGLISH_FUNCTION_WORDS = frozenset(
    "a is the you on in no me an it to of so we he be do at by or as if up my".split()
)

# Dialect markers that never occur in Modern Standard Arabic, matched whole-word
# against tashkeel-stripped tokens (see _arabic_bare_tokens).
# Two markers from the first draft of this list are deliberately absent:
#   * خلص — Levantine "enough", but also undiacriticised MSA form II خلّص
#     ("to rescue"), which is what ar_sentences.tsv row 9291 actually is
#     ("خلص ياني نفسه من الخيمة" = "Yanni freed himself from the tent"). Two of
#     its three hits were that verb; a marker that is a homograph of a common
#     MSA verb is noise, not a register signal.
#   * ايه/إيه are kept, but note they only survive because the scan does NOT
#     fold alef-maqsura or taa-marbuta: with the grader's full look-alike fold,
#     MSA أية/آية collapse onto ايه and produce 25 false hits.
# ده/دي (Egyptian demonstratives) are short enough to worry about; verified
# against all 14,671 rows of the Arabic sentence bank, they produce zero hits.
ARABIC_DIALECT_MARKERS = (
    "عايز عاوز مش بدي بدك فين ايه إيه ازيك إزيك دلوقتي كده كدا هيك شو ليش وين "
    "منيح بتاع معلش هاد هاي حكي ازاي إزاي عشان علشان دي ده"
).split()

# Hebrew niqqud, folded for the same reason as the Arabic marks.
_HEBREW_MARKS = re.compile(r"[֑-ׇ]")
_TATWEEL = "ـ"
# The inner ranges of the grader's tashkeel pattern, reused so the tokeniser
# below keeps together exactly the marks the fold strips.
_ARABIC_MARK_CLASS = _ARABIC_MARKS.pattern[1:-1]

_WORD_RE = re.compile(r"\w+", re.UNICODE)
# A "quoted construction" fragment: parenthesised, or trailing an arrow. These
# hold multiword target-language patterns ("because (car)", "trots op → er…op")
# whose authors consider printing the answer to be the convention.
_FRAGMENT_RE = re.compile(r"\(([^()]*)\)|[→⇒»](.*)$|(?:\.\.\.|…)(.*)$")
_GENDER_HINT_RE = re.compile(
    r"\((?:m|f|n|el|la|le|der|die|das|de|het|o|a|un|una)\)|"
    r"\bmasc(?:uline)?\b|\bfem(?:inine)?\b|\bneuter\b|"
    r"\bmasculin[oe]?\b|\bfeminin[aoe]?\b",
    re.IGNORECASE,
)
# Vowels stripped when testing whether several answers are the same morpheme
# under vowel harmony (Turkish mı/mi/mu/mü). Turkish dotless ı included.
_VOWELS = frozenset("aeiouyıàáâãäåæèéêëìíîïòóôõöøùúûüýÿœ")


def _nfc(text: str | None) -> str:
    return unicodedata.normalize("NFC", text or "")


def _fold_marks(code: str, text: str) -> str:
    """Drop combining marks a learner never types, for the languages that carry
    them. Both directions matter: an answer written with tashkeel would miss its
    bare quotation in a hint, and a marked-up hint word would match a shorter
    answer *inside* it, because combining marks are not word characters and so
    the \\w boundary reads them as a word break."""
    if code in ("ar", "fa"):
        return _ARABIC_MARKS.sub("", text).replace(_TATWEEL, "")
    if code == "he":
        return _HEBREW_MARKS.sub("", text)
    return text


def _whole_word(needle: str) -> re.Pattern[str]:
    """`needle` bounded so it cannot be part of a longer word. Lookarounds, not
    \\b: answers routinely start or end with punctuation (-ism, ¿, ‑) and \\b
    silently inverts its meaning there. This boundary IS the leak check's
    false-positive guard — 'trabaja' inside 'trabajar' must not match."""
    return re.compile(rf"(?<!\w){re.escape(needle)}(?!\w)", re.IGNORECASE | re.UNICODE)


def _resolved_sentence(drill: dict) -> str:
    return _nfc(drill.get("sentence")).replace("{{answer}}", _nfc(drill.get("answer")))


def _is_allomorph_set(answers: list[str]) -> bool:
    """True when several answers under one hint are harmony variants of a single
    morpheme, which is good pedagogy rather than an underdetermined drill: the
    sentence picks the variant, and that is the thing being taught.

    Heuristic: every answer is at most three characters and they differ only in
    their vowels, so the consonant skeleton is shared and non-empty (Turkish
    mı/mi/mu/mü -> 'm'). Answers made only of vowels are NOT exempt — 'a' vs 'e'
    share an empty skeleton without being related."""
    if not all(len(a) <= 3 for a in answers):
        return False
    skeletons = {"".join(c for c in a.casefold() if c not in _VOWELS) for a in answers}
    return len(skeletons) == 1 and bool(skeletons.pop())


def _quoted_construction(hint: str, answer: str) -> str | None:
    """The fragment of `hint` that quotes `answer` inside a construction, if any.

    'because (car)' and 'in order (um … zu)' hand over the answer, but the author
    is following the gloss-the-pattern convention rather than slipping. Needs the
    hint to say something outside the fragment (or the fragment to hold more than
    the answer), otherwise a hint that is nothing but the answer in brackets
    would be excused as a convention."""
    pattern = _whole_word(answer)
    for match in _FRAGMENT_RE.finditer(hint):
        fragment = next((g for g in match.groups() if g), "")
        if not fragment or not pattern.search(fragment):
            continue
        outside = hint[: match.start()] + hint[match.end() :]
        if len(_WORD_RE.findall(fragment)) >= 2 or _WORD_RE.search(outside):
            return fragment.strip()
    return None


def _arabic_bare_tokens(text: str) -> list[str]:
    """Word tokens of `text` with tashkeel and tatweel removed.

    The marks have to be inside the token class, not merely stripped afterwards:
    they are category Mn and Python's \\w does not match them, so a plain
    `(?<!\\w)فين(?!\\w)` scan reads المحلّفين ("jurors") as المحل + فين and reports
    Egyptian dialect inside a perfectly ordinary MSA word. Keeping the word whole
    and baring it afterwards is what makes the whole-word test mean anything."""
    return [
        _fold_marks("ar", raw)
        for raw in re.findall(rf"[\w{_TATWEEL}{_ARABIC_MARK_CLASS}]+", _nfc(text), re.UNICODE)
    ]


def load_grammar(code: str) -> list[dict] | None:
    """The grammar points for a language, or None when the file is absent."""
    path = GRAMMAR_DIR / f"{code}_grammar.json"
    if not path.exists():
        return None
    parsed = json.loads(path.read_text(encoding="utf-8"))
    return parsed.get("points", []) if isinstance(parsed, dict) else parsed


def load_morphology(code: str) -> dict | None:
    path = DATA / f"{code}_morphology.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _row_count(path: Path) -> int | None:
    """Data rows in a TSV (header excluded), or None when it does not exist.
    Counted by line rather than parsed: these files run to 200k rows and only
    their size matters here."""
    if not path.exists():
        return None
    with path.open(encoding="utf-8-sig") as handle:
        return max(sum(1 for _ in handle) - 1, 0)


def _empty_findings() -> dict[str, list[str]]:
    return {rule: [] for rule in ALL_RULES}


def audit_points(code: str, points: list[dict]) -> dict[str, list[str]]:
    """Every rule that reads drill text, for one language's grammar points.

    Split out from audit_language so the guards can be tested against synthetic
    drills without inventing a whole language on disk."""
    findings = _empty_findings()
    script = SCRIPT_RANGES.get(code)
    dialect_markers = frozenset(ARABIC_DIALECT_MARKERS) if code == "ar" else frozenset()

    for point in points:
        title = point.get("title", "?")
        if not _nfc(point.get("explanation")).strip():
            findings["empty"].append(f"[{title}] empty explanation")

        answers_by_hint: dict[str, set[str]] = defaultdict(set)
        for index, drill in enumerate(point.get("drills", []), start=1):
            answer = _nfc(drill.get("answer")).strip()
            hint = _nfc(drill.get("hint")).strip()
            translation = _nfc(drill.get("translation")).strip()
            sentence = _resolved_sentence(drill)

            if not hint:
                findings["empty"].append(f"[{title}] drill {index}: empty hint")
            if not translation:
                findings["empty"].append(f"[{title}] drill {index}: empty translation")

            if answer and hint:
                _audit_hint(code, findings, title, answer, hint, translation)

            if translation and sentence and code != "en":
                # `en` exempted: its translation field is a usage note by design
                # ("Clock time."), which made 46 of 46 hits false.
                if len(translation) < 0.4 * len(sentence):
                    findings["vague_translation"].append(
                        f'[{title}] "{sentence}" -> "{translation}"'
                    )

            if script and hint:
                residue = _whole_word(answer).sub("", hint) if answer else hint
                if len(re.findall(f"[{script}]+", residue)) >= 3:
                    findings["hint_language"].append(f"[{title}] answer '{answer}' hint '{hint}'")

            if dialect_markers:
                # One line per marker, not per occurrence: the answer is also
                # substituted into the sentence, so every drill would otherwise
                # count its own answer twice.
                text = " ".join((sentence, answer, translation))
                for token in sorted(set(_arabic_bare_tokens(text)) & dialect_markers):
                    findings["ar_register"].append(f"[{title}] '{token}' in \"{sentence}\"")

            if hint:
                # Casefolded on both sides: the same answer capitalised because
                # it opens a sentence is one answer, not an ambiguous pair.
                answers_by_hint[hint.casefold()].add(answer.casefold())

        for hint, answers in answers_by_hint.items():
            if len(answers) > 1 and not _is_allomorph_set(sorted(answers)):
                joined = ", ".join(sorted(answers))
                findings["duplicate_hint"].append(f"[{title}] hint '{hint}' -> {joined}")

    return findings


def _audit_hint(
    code: str,
    findings: dict[str, list[str]],
    title: str,
    answer: str,
    hint: str,
    translation: str,
) -> None:
    """The hint-versus-answer rules for a single drill."""
    match_answer = _fold_marks(code, answer)
    match_hint = _fold_marks(code, hint)
    leaks = bool(_whole_word(match_answer).search(match_hint))

    if leaks:
        # A short English function word matching inside English hint prose is a
        # collision, not a giveaway — unless the hint is nothing but the answer
        # (pt 'me | me', nl 'is | is' are real leaks).
        collision = (
            len(answer) <= 3
            and answer.casefold() in ENGLISH_FUNCTION_WORDS
            and hint.casefold() != answer.casefold()
        )
        if not collision:
            findings["leak_hard"].append(f"[{title}] answer '{answer}' in hint '{hint}'")

        fragment = _quoted_construction(match_hint, match_answer)
        if fragment:
            findings["construction_quote"].append(
                f"[{title}] answer '{answer}' quoted in '{fragment}' — hint '{hint}'"
            )

    # 'apakah — marks a yes/no question': the hint opens with its own answer and
    # explains it. 72 of 152 Indonesian and 86 of 152 Tagalog drills do this —
    # a generation template, not individual slips.
    if re.match(rf"^\s*{re.escape(match_answer)}\s*[—–-]", match_hint, re.IGNORECASE):
        findings["self_answering"].append(f"[{title}] hint '{hint}'")

    # A hint of a few words that already sits in the drill's own translation
    # ('she' for Ella under "She sings very well.") adds nothing, and for a
    # closed-class answer it determines the answer outright.
    words = _WORD_RE.findall(hint)
    if translation and 1 <= len(words) <= 3 and _whole_word(hint).search(translation):
        findings["giveaway_by_gloss"].append(
            f'[{title}] hint \'{hint}\' inside translation "{translation}"'
        )


def _audit_structure(code: str, points: list[dict] | None, morphology: dict | None) -> list[str]:
    """Content a language is missing entirely. Warn-level: a thin new language
    is a known state, not a regression, but it should never be a surprise."""
    problems = []
    if points is None:
        problems.append(f"data/grammar/{code}_grammar.json missing")

    # Two locations are legitimate: the bulk bank and the curated one. Some
    # languages carry only the curated file (jam has 15 rows in one, 356 in
    # the other), so neither path alone answers "is there a sentence bank".
    bulk = _row_count(DATA / f"{code}_sentences.tsv")
    curated = _row_count(DATA / "sentences" / f"{code}_sentences.tsv")
    if not (bulk or curated):
        problems.append(f"no sentence bank (data/{code}_sentences.tsv absent or empty)")

    frequency = _row_count(DATA / f"{code}_frequency.tsv")
    if frequency is None:
        problems.append(f"data/{code}_frequency.tsv missing")
    elif frequency < 1000:
        problems.append(f"data/{code}_frequency.tsv has only {frequency} rows (<1000)")

    if morphology is None:
        problems.append(f"data/{code}_morphology.json missing")
    elif not morphology:
        problems.append(f"data/{code}_morphology.json is an empty stub (0 entries)")
    elif not any(entry.get("chips") for entry in morphology.values()):
        problems.append(
            f"data/{code}_morphology.json has {len(morphology)} entries and no feature chips"
        )

    if not (DATA / "gym" / f"{code}.json").exists():
        problems.append(f"no Gym manifest (data/gym/{code}.json)")
    return problems


def _noun_genders(code: str, morphology: dict | None) -> dict[str, str]:
    """lowercased noun -> gender, from the morphology chips."""
    label = "Article" if code == "de" else "Gender"
    genders = {}
    for word, entry in (morphology or {}).items():
        if entry.get("pos") != "noun":
            continue
        value = next(
            (c.get("value") for c in entry.get("chips", []) if c.get("label") == label), None
        )
        if value:
            genders[_nfc(word).casefold()] = value
    return genders


def _audit_gender_marking(code: str, points: list[dict], morphology: dict | None) -> list[str]:
    """How often a noun-answer drill tells the learner the noun's gender. The
    data is there (Catalan morphology knows the gender of 98% of its nouns); the
    hints almost never say it, which is what "Catalan has gender problems"
    turned out to be."""
    if code not in GENDERED:
        return []
    genders = _noun_genders(code, morphology)
    if not genders:
        return ["gendered language with no machine-readable gender source"]
    total = marked = 0
    for point in points:
        for drill in point.get("drills", []):
            answer = _nfc(drill.get("answer")).strip().casefold()
            if answer not in genders:
                continue
            total += 1
            if _GENDER_HINT_RE.search(_nfc(drill.get("hint"))):
                marked += 1
    if not total:
        return ["no drill answers matched a noun in the morphology"]
    return [f"{marked}/{total} noun-answer drill hints mark gender ({100 * marked // total}%)"]


def _audit_arabic_sentences() -> list[str]:
    """Dialect markers in the Arabic sentence bank.

    The whole file is scanned, not a prefix: the only genuine hit in 14,671 rows
    sits at row 8204, so a sampled scan would have reported the bank clean.
    Both the headword and the sentence are checked — the headword is stemmer
    output and is where the artefacts show up."""
    path = DATA / "ar_sentences.tsv"
    if not path.exists():
        return []
    markers = frozenset(ARABIC_DIALECT_MARKERS)
    problems = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for number, row in enumerate(csv.DictReader(handle, delimiter="\t"), start=2):
            for column in ("word", "sentence"):
                hits = set(_arabic_bare_tokens(row.get(column) or "")) & markers
                for token in sorted(hits):
                    problems.append(
                        f"ar_sentences.tsv row {number} ({column}): '{token}' — "
                        f"\"{row.get('word')}\t{row.get('sentence')}\""
                    )
    return problems


def audit_language(code: str) -> dict:
    """Every rule for one language. Returns findings, counts and notes."""
    points = load_grammar(code)
    morphology = load_morphology(code)
    findings = audit_points(code, points or [])
    findings["structural"] = _audit_structure(code, points, morphology)
    findings["gender_marking"] = _audit_gender_marking(code, points or [], morphology)
    if code == "ar":
        findings["ar_register"] += _audit_arabic_sentences()

    drills = sum(len(p.get("drills", [])) for p in points or [])
    return {
        "code": code,
        "points": len(points or []),
        "drills": drills,
        "findings": findings,
        "counts": {rule: len(findings[rule]) for rule in ALL_RULES},
    }


def audit_all(codes: tuple[str, ...] | list[str] = LANGUAGES) -> list[dict]:
    return [audit_language(code) for code in codes]


def load_baseline() -> dict[str, int]:
    """Recorded fail-level debt, keyed "<lang>.<rule>". A missing key is zero,
    so a new language starts fully ratcheted."""
    if not BASELINE_PATH.exists():
        return {}
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def regressions(reports: list[dict], baseline: dict[str, int]) -> list[tuple[str, str, int, int]]:
    """(language, rule, count, allowed) for every fail-level count above its
    baseline. Equal is fine; the ratchet only ever turns one way."""
    out = []
    for report in reports:
        for rule in FAIL_RULES:
            count = report["counts"][rule]
            allowed = baseline.get(f"{report['code']}.{rule}", 0)
            if count > allowed:
                out.append((report["code"], rule, count, allowed))
    return out


def write_baseline(reports: list[dict]) -> dict[str, int]:
    """Rewrite the baseline for the languages just scanned, leaving the others
    alone so `--language xx --update-baseline` cannot silently zero the rest."""
    baseline = load_baseline()
    for report in reports:
        for rule in FAIL_RULES:
            key = f"{report['code']}.{rule}"
            count = report["counts"][rule]
            if count:
                baseline[key] = count
            else:
                baseline.pop(key, None)
    ordered = {key: baseline[key] for key in sorted(baseline)}
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(ordered, indent=1) + "\n", encoding="utf-8")
    return ordered


def print_report(reports: list[dict], examples: int = 5) -> None:
    for report in reports:
        code = report["code"]
        print(f"\n=== {code} — {report['points']} points, {report['drills']} drills ===")
        for group, rules in (("FAIL", FAIL_RULES), ("warn", WARN_RULES), ("note", REPORT_RULES)):
            for rule in rules:
                rows = report["findings"][rule]
                if not rows:
                    continue
                print(f"  {group} {rule}: {len(rows)}")
                for row in rows[:examples]:
                    print(f"      {row}")
                if len(rows) > examples:
                    print(f"      … {len(rows) - examples} more")
        if not any(report["counts"][rule] for rule in ALL_RULES):
            print("  clean")


def print_summary(reports: list[dict]) -> None:
    heads = ("leak", "self", "gloss", "dup", "empty", "ar_reg")
    print("\n" + "-" * 78)
    print(f"{'lang':<6}" + "".join(f"{h:>8}" for h in heads) + f"{'FAIL':>8}{'warn':>8}")
    for report in reports:
        counts = report["counts"]
        fails = sum(counts[rule] for rule in FAIL_RULES)
        warns = sum(counts[rule] for rule in WARN_RULES)
        cells = "".join(f"{counts[rule]:>8}" for rule in FAIL_RULES)
        print(f"{report['code']:<6}{cells}{fails:>8}{warns:>8}")
    total_fail = sum(sum(r["counts"][rule] for rule in FAIL_RULES) for r in reports)
    total_warn = sum(sum(r["counts"][rule] for rule in WARN_RULES) for r in reports)
    print(f"{'all':<6}{'':>48}{total_fail:>8}{total_warn:>8}")


def print_sample(code: str, count: int) -> None:
    """Random drills for the human spot-check protocol in docs/quality/README.md.
    Seeded from the language code so two people reading the same report are
    looking at the same drills."""
    points = load_grammar(code)
    if not points:
        print(f"{code}: no grammar file to sample")
        return
    drills = [(p, d) for p in points for d in p.get("drills", [])]
    rng = random.Random(code)
    for point, drill in rng.sample(drills, min(count, len(drills))):
        print(f"\n[{point.get('level')}] {point.get('title')}")
        print(f"  Q:      {drill.get('sentence')}")
        print(f"  answer: {drill.get('answer')}")
        print(f"  hint:   {drill.get('hint')}")
        print(f"  trans:  {drill.get('translation')}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.services.quality.audit_content",
        description="Mechanical content-quality audit with a baseline ratchet.",
    )
    parser.add_argument("--language", help="audit one language code instead of all 27")
    parser.add_argument("--json", dest="json_out", help="write the full findings to this path")
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="record today's fail-level counts as the new baseline",
    )
    parser.add_argument(
        "--sample",
        type=int,
        metavar="N",
        help="print N random drills for --language (human spot-check protocol)",
    )
    args = parser.parse_args(argv)

    if args.language and args.language not in LANGUAGES:
        parser.error(f"unknown language {args.language!r}; known: {' '.join(LANGUAGES)}")
    if args.sample:
        if not args.language:
            parser.error("--sample needs --language")
        print_sample(args.language, args.sample)
        return 0

    codes = (args.language,) if args.language else LANGUAGES
    reports = audit_all(codes)
    print_report(reports)
    print_summary(reports)

    if args.json_out:
        Path(args.json_out).write_text(
            json.dumps(reports, ensure_ascii=False, indent=1) + "\n", encoding="utf-8"
        )

    if args.update_baseline:
        ordered = write_baseline(reports)
        print(f"\nbaseline written: {BASELINE_PATH.relative_to(REPO)} ({len(ordered)} entries)")
        return 0

    failures = regressions(reports, load_baseline())
    print()
    for code, rule, count, allowed in failures:
        print(f"REGRESSION {code}.{rule}: {count} (baseline {allowed})")
    if failures:
        print(f"FAIL — {len(failures)} rule(s) above baseline. Fix the content, or, if the "
              "increase is intended and explained in the commit, --update-baseline.")
        return 1
    print("PASS — no fail-level rule exceeds its baseline.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
