"""Russian vocabulary seeder using OpenRussian TSV data."""
import csv
import json
import logging
import httpx

from .base import BaseSeeder, DATA_DIR

WORDS_URL = "https://downloads.openrussian.org/ru/words.tsv"
TRANSLATIONS_URL = "https://downloads.openrussian.org/ru/translations.tsv"

# Filenames as module-level constants so tests can patch DATA_DIR
WORDS_FILENAME = "ru_words.tsv"
TRANSLATIONS_FILENAME = "ru_translations.tsv"


class RussianSeeder(BaseSeeder):
    language_code = "ru"

    async def download(self) -> None:
        """Download OpenRussian words.tsv and translations.tsv to DATA_DIR."""
        DATA_DIR.mkdir(parents=True, exist_ok=True)

        for url, filename in [
            (WORDS_URL, WORDS_FILENAME),
            (TRANSLATIONS_URL, TRANSLATIONS_FILENAME),
        ]:
            path = DATA_DIR / filename
            if path.exists():
                self.logger.info(f"{filename} already exists, skipping download")
                continue
            self.logger.info(f"Downloading {url}...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.get(url, follow_redirects=True)
                resp.raise_for_status()
                path.write_bytes(resp.content)
            self.logger.info(f"Downloaded {filename} ({path.stat().st_size} bytes)")

    async def transform(self) -> list[dict]:
        """Parse OpenRussian TSV into vocabulary records."""
        # Use module globals so tests can patch DATA_DIR and WORDS_FILENAME
        import backend.services.seeder.seed_russian as _mod
        data_dir = _mod.DATA_DIR
        words_path = data_dir / _mod.WORDS_FILENAME
        translations_path = data_dir / _mod.TRANSLATIONS_FILENAME

        # Parse translations first (word_id → {locale: definition})
        trans_map: dict[str, dict[str, str]] = {}
        with open(translations_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                word_id = row.get("word_id", "")
                lang = row.get("lang", "en")
                text = row.get("tl", "").strip()
                if word_id and text:
                    trans_map.setdefault(word_id, {})[lang] = text

        # Try to load pymorphy3 for morphological enrichment
        try:
            import pymorphy3
            morph = pymorphy3.MorphAnalyzer()
        except ImportError:
            morph = None
            self.logger.warning("pymorphy3 not available — morphology will be empty")

        records = []
        with open(words_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if row.get("disabled", "0") == "1":
                    continue

                word_id = row.get("id", "")
                bare = row.get("bare", "").strip()
                accented = row.get("accented", "").strip()
                rank_str = row.get("rank", "") or row.get("position", "")

                if not bare:
                    continue

                rank = int(rank_str) if rank_str and rank_str.isdigit() else None

                # reading is the accented form only when it differs from bare
                reading = accented if accented and accented != bare else None

                # Morphology enrichment from pymorphy3
                morphology: dict = {}
                pos = None
                if morph:
                    parsed = morph.parse(bare)
                    if parsed:
                        p = parsed[0]
                        pos = str(p.tag.POS) if p.tag.POS else None
                        raw_morph = {
                            "gender": str(p.tag.gender) if p.tag.gender else None,
                            "aspect": str(p.tag.aspect) if p.tag.aspect else None,
                            "animacy": str(p.tag.animacy) if p.tag.animacy else None,
                        }
                        # Remove None/"None" values for clean JSONB
                        morphology = {
                            k: v for k, v in raw_morph.items()
                            if v and v != "None"
                        }

                translations = trans_map.get(word_id, {})

                records.append({
                    "word": bare,
                    "reading": reading,
                    "pos": pos,
                    "level": self.rank_to_level(rank),
                    "frequency_rank": rank,
                    "morphology": json.dumps(morphology, ensure_ascii=False),
                    "translations": translations,
                })

        self.logger.info(f"Transformed {len(records)} Russian words")
        return records
