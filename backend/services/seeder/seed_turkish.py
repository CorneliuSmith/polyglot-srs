"""Turkish vocabulary seeder from a bundled frequency + translation TSV.

Expected file format (tab-separated, header row):
    rank	word	pos	en
    1	bir	det	a, one
    2	ve	conj	and

Data source suggestion: an OpenSubtitles 2018 Turkish frequency list merged
with Wiktionary translations — drop the merged TSV at data/tr_frequency.tsv.
"""
import csv
import json

from backend.services.nlp.turkish import turkish_lower

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — DATA_DIR re-exported so tests can patch it

FREQ_FILENAME = "tr_frequency.tsv"


class TurkishSeeder(BaseSeeder):
    language_code = "tr"

    async def download(self) -> None:
        """No automatic download — the merged TSV is bundled manually."""
        import backend.services.seeder.seed_turkish as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Turkish frequency file not found at %s — place the TSV there", path
            )

    async def transform(self) -> list[dict]:
        """Parse the frequency TSV into vocabulary records."""
        import backend.services.seeder.seed_turkish as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Turkish frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # Turkish casing matters: 'I' must lower to 'ı', not 'i'
                word = turkish_lower(row["word"].strip())
                translation = (row.get("en") or "").strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                # Vowel-harmony spellings of ONE word, from the file's `alt`
                # column (semicolon-separated, as Jamaican's is). The yes/no
                # particle is mi, mı, mu or mü depending on the vowel before
                # it; the course used to carry the four as separate headwords
                # with one shared definition, so a learner on any of the four
                # cards could not know which spelling to type. One card now,
                # graded correct for any of its forms (nlp/base.py layer 6),
                # with a definition that states the rule rather than which
                # vowel class won — tr.md, hint standard 2 (7 Sep 2026).
                alts = [
                    turkish_lower(a.strip())
                    for a in (row.get("alt") or "").split(";")
                    if a.strip()
                ]
                record = {
                    "word": word,
                    "reading": None,
                    "pos": (row.get("pos") or "").strip() or None,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "morphology": json.dumps({"lemma": word}, ensure_ascii=False),
                    "translations": {"en": translation},
                }
                if alts:
                    record["alternatives"] = alts
                records.append(record)

        self.logger.info(f"Transformed {len(records)} Turkish words")
        return records
