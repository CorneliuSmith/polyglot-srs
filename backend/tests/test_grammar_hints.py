"""Grammar-drill hint quality: a conjugation/declension drill's hint is the
Gym "baseline" cue, so it must be in the TARGET language ("<infinitive>,
<person>"), not an English gloss ("to work (she)", "yo form of ser").

The languages whose base form is an infinitive (Romance/Germanic) or a
lemmatizable citation form (Russian) were cleaned to "<base>, <person>" and are
locked here. The four still-English languages are HELD on purpose: ar (Semitic —
no infinitive; hints describe the prefix), el (Greek cites the 1sg present, not
an infinitive), tr (agglutinative), xh (Bantu). Their base-form model is
different and needs a native/LLM pass, so they're reported, not failed.
"""
from __future__ import annotations

import glob
import json
import re

# An English gloss where a target-language "<base>, <person>" cue belongs.
_ENGLISH_HINT = re.compile(r"\bto\s+[a-z]+\b|\bform of\b", re.I)

# Languages converted to target-language "<base>, <person>" — must stay at zero.
_CLEAN = {"es", "fr", "it", "ca", "ro", "de", "ru"}

# Held on purpose (base form isn't a derivable infinitive): reported, not failed.
_HELD = {"ar", "el", "tr", "xh"}


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
        print("\nEnglish conjugation-hint debt (held for a native/LLM pass):")
        for code, n in sorted(report.items(), key=lambda kv: -kv[1]):
            print(f"  {code}: {n}")
    # The cleaned languages must not appear; only the held set may remain.
    assert not (_CLEAN & report.keys()), report
    assert report.keys() <= _HELD, f"unexpected debt outside the held set: {report}"
