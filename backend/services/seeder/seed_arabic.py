"""Arabic vocabulary seeder using a curated bundled seed file."""
import json

from .base import DATA_DIR, BaseSeeder


class ArabicSeeder(BaseSeeder):
    language_code = "ar"

    async def download(self) -> None:
        """Arabic uses a bundled seed file — no download needed."""
        seed_path = DATA_DIR / "ar_seed.json"
        if not seed_path.exists():
            raise FileNotFoundError(
                f"Arabic seed file not found at {seed_path}. "
                "Copy data/ar_seed.json to the data directory."
            )

    async def transform(self) -> list[dict]:
        """Parse Arabic seed JSON into vocabulary records."""
        import backend.services.seeder.seed_arabic as _mod

        seed_path = _mod.DATA_DIR / "ar_seed.json"
        raw = json.loads(seed_path.read_text(encoding="utf-8"))

        # Optional: enrich with camel-tools if available
        analyzer = None
        try:
            from camel_tools.morphology.analyzer import Analyzer
            from camel_tools.morphology.database import MorphologyDB

            db = MorphologyDB.builtin_db()
            analyzer = Analyzer(db)
        except (ImportError, Exception):
            self.logger.warning("camel-tools not available — using seed file morphology only")

        records = []
        for item in raw:
            morphology: dict = {
                "root": item.get("root"),
                "form": item.get("form"),
                "gender": item.get("gender"),
                "pattern": item.get("pattern"),
            }

            # Enrich with camel-tools if available
            if analyzer:
                try:
                    analyses = analyzer.analyze(item["word"])
                    if analyses:
                        best = analyses[0]
                        morphology.setdefault("root", best.get("root", ""))
                        morphology.setdefault("pattern", best.get("pattern", ""))
                        morphology.setdefault("form", best.get("vform", ""))
                except Exception:
                    pass

            # Remove None values for clean JSONB
            morphology = {k: v for k, v in morphology.items() if v is not None}

            records.append({
                "word": item["word"],
                "reading": item.get("reading"),
                "pos": item.get("pos"),
                "level": self.rank_to_level(item.get("rank")),
                "frequency_rank": item.get("rank"),
                "morphology": json.dumps(morphology, ensure_ascii=False),
                "translations": item.get("translations", {}),
            })

        self.logger.info(f"Transformed {len(records)} Arabic words")
        return records
