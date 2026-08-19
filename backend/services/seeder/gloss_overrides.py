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
