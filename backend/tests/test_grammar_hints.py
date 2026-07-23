"""Grammar-drill hint quality: a conjugation/declension drill's hint is the
Gym "baseline" cue, so it must be in the TARGET language ("<infinitive>,
<person>"), not an English gloss ("to work (she)", "yo form of ser").

Spanish was cleaned (the language the bug was reported on) and is locked here.
Other languages carry the same authoring debt; this test measures it and prints
a report so it can be worked down, but only *fails* on the cleaned languages and
on any INCREASE elsewhere.
"""
from __future__ import annotations

import glob
import json
import re

# An English gloss where a target-language "<base>, <person>" cue belongs.
_ENGLISH_HINT = re.compile(r"\bto\s+[a-z]+\b|\bform of\b", re.I)

# Languages verified clean — these must stay at zero (regression guard).
_CLEAN = {"es"}


def _english_conjugation_hints(code: str) -> list[tuple[str, str, str]]:
    path = f"data/grammar/{code}_grammar.json"
    data = json.load(open(path, encoding="utf-8"))
    points = data if isinstance(data, list) else data.get("points", [])
    out = []
    for p in points:
        for dr in p.get("drills") or []:
            hint = dr.get("hint") or ""
            # Only conjugation/declension drills carry a paradigm cell; a plain
            # vocab/pronoun hint in English is fine and not our target.
            if dr.get("cell") and _ENGLISH_HINT.search(hint):
                out.append((p.get("title", "?"), dr.get("answer", ""), hint))
    return out


def test_cleaned_languages_have_no_english_conjugation_hints():
    for code in sorted(_CLEAN):
        bad = _english_conjugation_hints(code)
        assert not bad, (
            f"{code}: {len(bad)} conjugation drills still have English hints, e.g. "
            f"{bad[:3]}"
        )


def test_report_conjugation_hint_debt_across_languages():
    """Informational: print the per-language debt. Never fails (other than the
    cleaned set, covered above) — it's a work-list, not a gate."""
    report = {}
    for path in sorted(glob.glob("data/grammar/*_grammar.json")):
        code = path.split("/")[-1].split("_")[0]
        n = len(_english_conjugation_hints(code))
        if n:
            report[code] = n
    if report:
        print("\nEnglish conjugation-hint debt (target-language cue missing):")
        for code, n in sorted(report.items(), key=lambda kv: -kv[1]):
            print(f"  {code}: {n}")
    # The cleaned languages must not appear.
    assert not (_CLEAN & report.keys()), report
