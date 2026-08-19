"""Write English's definitions into data/en_frequency.tsv.

Every other course commits `rank / word / pos / en` and is auditable from the
file alone. English resolved its definitions from WordNet at seed time, so
nothing in the repo recorded what a learner would actually be shown — which is
how rank 3 `be` shipped as "a light strong brittle grey toxic bivalent
metallic element" without a single check firing.

Run this after changing data/gloss_overrides.tsv or the sense-selection rules:

    .venv/bin/python -m backend.services.seeder.emit_english_glosses

It needs NLTK's WordNet corpus. Seeding does not: the file it writes is what
the seeder reads.

The `pos` column is WordNet's, and seeding still lets spaCy refine it for
words no override pins — so treat it as the fallback it is, not as a record of
what ships.
"""
import asyncio
import csv
import sys

from .base import DATA_DIR
from .seed_english import FREQ_FILENAME, EnglishSeeder

FIELDS = ("rank", "word", "pos", "en")


class _Regenerating(EnglishSeeder):
    """Resolves every definition from WordNet, ignoring what is on disk."""

    use_committed_glosses = False


async def build() -> list[dict]:
    records = await _Regenerating("postgresql://unused/emit").transform()
    by_word = {r["word"]: r for r in records}

    path = DATA_DIR / FREQ_FILENAME
    with open(path, encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))

    out = []
    for row in rows:
        word = (row.get("word") or "").strip()
        rec = by_word.get(word)
        out.append({
            "rank": (row.get("rank") or "").strip(),
            "word": word,
            # A word the seeder dropped (no WordNet sense, or tokenizer
            # shrapnel) keeps its rank and stays blank rather than vanishing:
            # the file is the frequency list first and the gloss table second.
            "pos": (rec["pos"] or "") if rec else (row.get("pos") or ""),
            "en": (rec["translations"]["en"] if rec else (row.get("en") or "")),
        })
    return out


def main() -> int:
    rows = asyncio.run(build())
    path = DATA_DIR / FREQ_FILENAME
    with open(path, "w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS, delimiter="\t",
                                lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    filled = sum(1 for r in rows if r["en"])
    print(f"wrote {len(rows)} rows to {path} ({filled} with a definition)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
