"""Jamaican Patois (jam) vocabulary seeder.

Hand-authored core vocabulary in the Cassidy/JLU phonemic orthography —
no OpenSubtitles list or kaikki extract exists for Jamaican Creole, so the
corpus is curated (like Hausa's plural-carrying seed). File format adds an
`alt` column carrying the common English-based spellings ("likkle" for
likl, "pickney" for pikni); they load into vocabulary.alternatives so the
grader accepts either convention. Draft tier: everything ships for native
review (beta rollout plan gates the tier on a JLU-connected reviewer).
"""
import csv
import json

from .base import DATA_DIR, BaseSeeder  # noqa: F401 — re-exported so tests can patch it

FREQ_FILENAME = "jam_frequency.tsv"


class JamaicanSeeder(BaseSeeder):
    language_code = "jam"

    async def download(self) -> None:
        import backend.services.seeder.seed_jamaican as _mod

        path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not path.exists():
            self.logger.warning(
                "Jamaican frequency file not found at %s — it is curated "
                "and versioned in data/, not downloaded", path
            )

    async def transform(self) -> list[dict]:
        import backend.services.seeder.seed_jamaican as _mod

        freq_path = _mod.DATA_DIR / _mod.FREQ_FILENAME
        if not freq_path.exists():
            raise FileNotFoundError(f"Frequency file not found at {freq_path}")

        records = []
        seen: set[str] = set()
        with open(freq_path, encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                word = row["word"].strip().lower()
                translation = (row.get("en") or "").strip()
                if not word or not translation or word in seen:
                    continue
                seen.add(word)
                rank = int(row["rank"])
                alts = [
                    a.strip().lower()
                    for a in (row.get("alt") or "").split(";")
                    if a.strip()
                ]
                morphology = {"lemma": word}
                if alts:
                    morphology["spellings"] = alts
                record = {
                    "word": word,
                    "reading": None,
                    "pos": (row.get("pos") or "").strip() or None,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "morphology": json.dumps(morphology, ensure_ascii=False),
                    "translations": {"en": translation},
                }
                if alts:
                    # English-based spellings grade as correct answers.
                    record["alternatives"] = alts
                records.append(record)

        # Proportional banding by hand: rank_to_level's proportional mode
        # guards at >=500 words (so 30-word starters stay all-A1), but this
        # 384-word CURATED list is the whole corpus — band it 5/15/30/50/80%
        # like the big lists so the ladder reaches C1/C2 instead of dumping
        # everything into one A1 deck.
        total = len(records)
        for rec in records:
            rank = rec.get("frequency_rank")
            if rank is None:
                continue
            frac = rank / total
            if frac <= 0.05:
                rec["level"] = "A1"
            elif frac <= 0.15:
                rec["level"] = "A2"
            elif frac <= 0.30:
                rec["level"] = "B1"
            elif frac <= 0.50:
                rec["level"] = "B2"
            elif frac <= 0.80:
                rec["level"] = "C1"
            else:
                rec["level"] = "C2"

        self.logger.info(f"Transformed {len(records)} Jamaican Patois words")
        return records
