"""The one file where a wrong definition gets corrected by hand.

Kept in its own module, importing nothing but the standard library, because
both source_data (which corrects glosses read from a corpus) and seed_english
(which builds them from WordNet at seed time) need it, and the English seeder
should not have to import a web client to read a TSV.
"""
import csv
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[3] / "data"
GLOSS_OVERRIDES_PATH = DATA_DIR / "gloss_overrides.tsv"


def load_gloss_overrides(language: str, path: Path | None = None) -> dict[str, dict]:
    """word -> {pos, en} for *language*, from the shared override file.

    *path* defaults to the committed file. Callers pass their own module's
    copy of the constant so a test that monkeypatches it there is still
    obeyed — moving this function out of source_data silently broke two
    tests that patch source_data.GLOSS_OVERRIDES_PATH.
    """
    path = path or GLOSS_OVERRIDES_PATH
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            if (row.get("language") or "").strip() != language:
                continue
            word = (row.get("word") or "").strip()
            if word:
                out[word] = {
                    "pos": (row.get("pos") or "").strip(),
                    "en": (row.get("en") or "").strip(),
                }
    return out


def apply_gloss_overrides_to_records(
    language: str, records: list[dict], path: Path | None = None,
) -> int:
    """Overlay the hand-authored definitions onto seeder records, in place.

    Until 7 Sep 2026 the override file reached production by exactly one
    road: `source_data --language X` rebuilt the frequency TSV with the
    overrides folded into its `en` column, and the seeder and the reconcile
    both read that column. A definition written to the override file WITHOUT
    a rebuild reached nothing — which is what the Phase 2d pass did for
    1,611 definitions across 25 courses (quality rule 13: a layer with no
    write path cannot ship). The English seeder had always overlaid the file
    itself; now every seeder does, here, and the reconcile compares against
    the same overlay (`reconcile.expected_rows`), so a re-seed can no longer
    revert a corrected definition to the file's stale column either.

    An override never invents a record: rank comes from the corpus. Returns
    the number of records touched.
    """
    overrides = load_gloss_overrides(language, path)
    if not overrides:
        return 0
    applied = 0
    for rec in records:
        hit = overrides.get(rec.get("word") or "")
        if not hit:
            continue
        gloss, pos = hit.get("en") or "", hit.get("pos") or ""
        if not (gloss or pos):
            continue
        if gloss:
            translations = dict(rec.get("translations") or {})
            translations["en"] = gloss
            rec["translations"] = translations
        if pos:
            rec["pos"] = pos
        applied += 1
    return applied

