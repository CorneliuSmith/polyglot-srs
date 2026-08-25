"""Cards that grade identically to another card, per language.

The failure this reports was found in Latin. `data/la_frequency.tsv` had gone
half-macronised, so 40 spellings collided once `LatinNLP` folded the macrons —
40 pairs of cards with one gradable answer between them, invisible to every
test because both members graded the same. Measuring the same thing with each
language's OWN grader turned up 2,122 across eleven courses: typing `el` (the)
against `él` (he) returned CORRECT_SLOPPY, full credit, and the scheduler then
filed `él` as known.

Two keys are measured, because the grader uses both and they catch different
things:

  strip-key  what BaseNLP layer 2.5 compares — the answer with combining
             marks removed. Catches á/a, ё/е, ā/a.
  fold-key   what AccentFoldingNLP.lemmatize compares. Catches everything the
             strip-key does plus marks with no combining decomposition —
             Romanian ș/ț, German ß→ss — which is why `ro si`/`și` is invisible
             to the first and not the second.

A nonzero count is not automatically debt. Most collisions in an
accent-keeping language are CONTRASTIVE pairs — real distinct words the
collision guard exists to protect (`de`/`dé`, `schon`/`schön`). What this
instrument is for is (a) producing the ceilings frozen in
backend/tests/test_nlp_collisions.py, and (b) noticing when a course GROWS the
class, which is how Latin's 40 got in unseen.

Reads the committed TSVs and the real NLP backends: no database, no API key,
no network.

Usage:
    python -m backend.services.quality.audit_collisions
    python -m backend.services.quality.audit_collisions --language es --detail
    python -m backend.services.quality.audit_collisions --ceilings
"""
from __future__ import annotations

import argparse
import csv
import unicodedata
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "data"

LANGUAGES = tuple(
    "ru ar en sw tr yo ha xh es it fr de ca mi ro el pt hi jam nl th ko "
    "la id tl he fa".split()
)


def strip_marks(text: str) -> str:
    """Drop combining marks — what grading layer 2.5 compares."""
    return "".join(
        c for c in unicodedata.normalize("NFD", text) if not unicodedata.combining(c)
    )


def _rows(code: str) -> list[dict]:
    path = DATA / f"{code}_frequency.tsv"
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return [r for r in csv.DictReader(handle, delimiter="\t")
                if (r.get("word") or "").strip()]


def audit_language(code: str, backends: dict) -> dict:
    """Collision counts and groups for one course."""
    rows = _rows(code)
    nlp = backends.get(code)
    if not rows or nlp is None:
        return {"code": code, "rows": len(rows), "strip": 0, "fold": 0, "groups": []}

    surfaces = [(r, nlp.normalize(r["word"])) for r in rows]

    def collide(key):
        buckets: dict[str, list[dict]] = defaultdict(list)
        for row, norm in surfaces:
            buckets[key(norm)].append(row)
        return {k: v for k, v in buckets.items() if len(v) > 1}

    strip_groups = collide(strip_marks)
    fold_groups = (
        collide(nlp._fold) if hasattr(nlp, "_fold") else strip_groups
    )
    counted = sum(len(v) - 1 for v in strip_groups.values())
    folded = sum(len(v) - 1 for v in fold_groups.values())

    groups = sorted(
        (sorted(v, key=lambda r: int(r["rank"])) for v in fold_groups.values()),
        key=lambda v: int(v[0]["rank"]),
    )
    return {"code": code, "rows": len(rows), "strip": counted, "fold": folded,
            "groups": groups}


def audit_all(codes=LANGUAGES) -> list[dict]:
    from backend.services import nlp as nlp_module

    nlp_module.init_nlp_backends()
    return [audit_language(c, nlp_module.NLP_BACKENDS) for c in codes]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--language", "-l", choices=LANGUAGES)
    parser.add_argument("--detail", action="store_true",
                        help="list the colliding groups, lowest rank first")
    parser.add_argument("--ceilings", action="store_true",
                        help="emit the dict literal for test_nlp_collisions.py")
    args = parser.parse_args()

    codes = (args.language,) if args.language else LANGUAGES
    reports = audit_all(codes)

    if args.ceilings:
        print(", ".join(f'"{r["code"]}": {r["strip"]}' for r in reports))
        return 0

    print("Cards that grade identically to another card, by each language's own grader.")
    print("Most are CONTRASTIVE pairs the collision guard protects — see")
    print("docs/quality/CHECKS.md §3. Watch for a course that GROWS the number.\n")
    print(f"{'lang':<6}{'rows':>7}{'strip-key':>11}{'fold-key':>10}")
    print("-" * 34)
    for r in reports:
        print(f"{r['code']:<6}{r['rows']:>7}{r['strip']:>11}{r['fold']:>10}")
    print("-" * 34)
    print(f"{'all':<6}{sum(r['rows'] for r in reports):>7}"
          f"{sum(r['strip'] for r in reports):>11}"
          f"{sum(r['fold'] for r in reports):>10}")

    if args.detail:
        for r in reports:
            if not r["groups"]:
                continue
            print(f"\n{r['code']} — {len(r['groups'])} colliding groups")
            for group in r["groups"][:40]:
                members = " | ".join(
                    f"r{m['rank']} {m['word']!r} {(m.get('en') or '')[:30]}" for m in group
                )
                print(f"  {members}")
            if len(r["groups"]) > 40:
                print(f"  … {len(r['groups']) - 40} more")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
