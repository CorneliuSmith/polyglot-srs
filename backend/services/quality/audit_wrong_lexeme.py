"""Find rows where a GRAMMATICAL form's rank was given a LEXICAL word's gloss.

This is `docs/quality/CHECKS.md` §3b. Every instance was found by hand until
25 Aug 2026, when this screen was written and turned up 351 candidates in the
top 500 alone — 248 of them real, including Catalan's entire core present
tense (`estic` "hockey stick" for "I am") and French rank 55 `va` glossed
"version anglaise", a film-dubbing abbreviation, where the word means "goes".

**The mechanism.** A frequency list is built from running text, so a rank is
earned by whatever string appeared. Where a spelling is BOTH an inflection of
a common verb and a separate dictionary word, the sense-picker sometimes took
the dictionary word — and a bigger corpus supplies MORE obscure homographs to
lose to, so row count is not a proxy for quality.

**The signature.** kaikki marks the distinction itself: an inflection carries
`form-of` in its sense tags plus a `form_of` lemma; contractions and
abbreviations carry their own tags. So a candidate is a row where

  1. kaikki lists both a grammatical and a lexical sense for the word,
  2. the grammatical sense points at a lemma THIS COURSE ALSO TEACHES, and
  3. the committed gloss reads like the lexical sense and not the grammatical.

Condition 2 is what makes the screen usable. Without it the same query returns
1,227 rows, mostly noise: Xhosa `uku-` infinitives really are nouns, and
Indonesian `api` is "fire" whatever else kaikki lists for it.

**This screens; it does not judge.** Roughly 70% of its candidates were real in
the first sweep, so every hit needs a reviewer. It cannot see a word kaikki
lacks, and it says nothing when only one kind of sense exists.

**It needs `data/raw/<code>_kaikki.jsonl`, which is gitignored** (8 GB of
extracts). So this is a maintenance tool run locally when the extracts are
present, NOT a CI check — unlike `audit_content`, it cannot fail a build.

    python -m backend.services.quality.audit_wrong_lexeme --band 500
    python -m backend.services.quality.audit_wrong_lexeme --lang fr --json out.json
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import unicodedata
from pathlib import Path

DATA = Path(__file__).resolve().parents[3] / "data"
RAW = DATA / "raw"

_TOKEN = re.compile(r"[a-z']+")
GRAMMATICAL_TAGS = {"form-of", "alt-of", "abbreviation", "contraction", "participle"}
_STOP = frozenset(
    "a an the of to in on at by for with from and or but is are be it its as that this".split()
)


def _norm(text: str | None) -> str:
    return unicodedata.normalize("NFC", (text or "").strip()).lower()


def _tokens(text: str | None) -> set[str]:
    return {t for t in _TOKEN.findall((text or "").lower()) if t not in _STOP and len(t) > 2}


def _overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a) if a and b else 0.0


def _band_rows(code: str, band: int) -> list[dict]:
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return []
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            try:
                rank = int(row.get("rank") or 0)
            except ValueError:
                continue
            if 0 < rank <= band and (row.get("word") or "").strip() and (row.get("en") or "").strip():
                rows.append({"rank": rank, "word": row["word"],
                             "pos": row.get("pos", ""), "en": row["en"]})
    return rows


def _senses(code: str, wanted: set[str]) -> dict[str, list[dict]]:
    """Every kaikki sense for the wanted words, tagged grammatical or not."""
    path = RAW / f"{code}_kaikki.jsonl"
    out: dict[str, list[dict]] = {}
    if not path.exists():
        return out
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except ValueError:
                continue
            word = _norm(entry.get("word"))
            if word not in wanted:
                continue
            pos = (entry.get("pos") or "").lower()
            for sense in entry.get("senses") or []:
                gloss = (sense.get("glosses") or [""])[0]
                if not gloss:
                    continue
                tags = set(sense.get("tags") or [])
                lemmas = [
                    _norm(x.get("word"))
                    for x in (sense.get("form_of") or sense.get("alt_of") or [])
                    if isinstance(x, dict) and x.get("word")
                ]
                out.setdefault(word, []).append({
                    "gloss": gloss, "lemma": lemmas[0] if lemmas else "",
                    "grammatical": bool(tags & GRAMMATICAL_TAGS) or bool(lemmas)
                    or pos in ("contraction", "abbrev"),
                })
    return out


def candidates(code: str, band: int = 500) -> list[dict]:
    rows = _band_rows(code, band)
    if not rows:
        return []
    in_course = {_norm(r["word"]) for r in rows}
    senses = _senses(code, in_course)
    found = []
    for row in rows:
        word = _norm(row["word"])
        entries = senses.get(word)
        if not entries:
            continue
        # A form only plausibly OWNS a rank when its lemma is a word this
        # course teaches: `pelo` -> `por` is a real mis-pick, `api` -> an
        # aviation-academy initialism is not.
        grammatical = [s for s in entries
                       if s["grammatical"] and s["lemma"] in in_course and s["lemma"] != word]
        lexical = [s for s in entries if not s["grammatical"]]
        if not grammatical or not lexical:
            continue
        committed = _tokens(row["en"].split(";")[0])
        best_lexical = max((_overlap(_tokens(s["gloss"]), committed) for s in lexical), default=0.0)
        best_grammatical = max((_overlap(_tokens(s["gloss"]), committed) for s in grammatical), default=0.0)
        if best_lexical >= 0.5 and best_grammatical < 0.34:
            found.append({
                "lang": code, "rank": row["rank"], "word": row["word"],
                "pos": row["pos"], "committed_gloss": row["en"],
                "kaikki_grammatical": [{"gloss": s["gloss"][:200], "lemma": s["lemma"]}
                                       for s in grammatical][:6],
                "kaikki_lexical": [s["gloss"][:200] for s in lexical][:6],
            })
    return found


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--band", type=int, default=500, help="how deep to screen")
    parser.add_argument("--lang", help="one language code; default every course with an extract")
    parser.add_argument("--json", help="write the candidates here for a review pass")
    args = parser.parse_args()

    codes = [args.lang] if args.lang else sorted(
        p.name.split("_")[0] for p in DATA.glob("*_frequency.tsv")
    )
    missing, everything = [], []
    for code in codes:
        if not (RAW / f"{code}_kaikki.jsonl").exists():
            missing.append(code)
            continue
        hits = candidates(code, args.band)
        everything.extend(hits)
        print(f"{code:<5}{len(hits):>5} candidates in the top {args.band}")
        for hit in hits[:4]:
            print(f"      r{hit['rank']:<5}{hit['word']:<16}{hit['committed_gloss'][:46]}")
            print(f"      {'':<21}kaikki: {hit['kaikki_grammatical'][0]['gloss'][:52]}")
    if missing:
        print(f"\nno kaikki extract, not screened: {', '.join(missing)}")
    print(f"\ntotal {len(everything)} candidates — these need a reviewer, not a rewrite")
    if args.json:
        Path(args.json).write_text(json.dumps(everything, ensure_ascii=False, indent=1),
                                   encoding="utf-8")
        print(f"written to {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
