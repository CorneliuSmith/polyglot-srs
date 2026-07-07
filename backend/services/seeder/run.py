"""CLI runner for vocabulary seed scripts.

Usage:
    python -m backend.services.seeder.run --language ru
    python -m backend.services.seeder.run --language all
    python -m backend.services.seeder.run --language ar --db-url postgresql://...
    python -m backend.services.seeder.run --file vocab.csv --language ar
"""
import argparse
import asyncio
import logging
import os


async def main():
    parser = argparse.ArgumentParser(description="Seed vocabulary data into the database")
    parser.add_argument(
        "--language", "-l",
        choices=["ru", "ar", "en", "sw", "tr", "yo", "ha", "xh",
                 "es", "it", "fr", "de", "ca", "mi", "ro", "el", "all"],
        default="all",
        help="Language to seed (default: all)",
    )
    parser.add_argument(
        "--db-url",
        default=os.environ.get("DATABASE_URL"),
        help="PostgreSQL connection URL (or set DATABASE_URL env var)",
    )
    parser.add_argument(
        "--file", "-f",
        help="Import vocabulary from a CSV or TSV file (requires --language, cannot be 'all')",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")

    if not args.db_url:
        print("ERROR: DATABASE_URL not set. Pass --db-url or set DATABASE_URL env var.")
        return

    # --file mode: route to CSVImporter instead of built-in seeders
    if args.file:
        if not args.language or args.language == "all":
            print("ERROR: --language is required when using --file (cannot be 'all')")
            return
        from .csv_importer import CSVImporter
        seeder = CSVImporter(args.db_url, args.language, args.file)
        try:
            count = await seeder.run()
            print(f"OK {seeder.language_code}: {count} words loaded from {args.file}")
        except Exception as e:
            print(f"FAIL {seeder.language_code}: {e}")
        return

    seeders = []
    if args.language in ("ru", "all"):
        from .seed_russian import RussianSeeder
        seeders.append(RussianSeeder(args.db_url))
    if args.language in ("ar", "all"):
        try:
            from .seed_arabic import ArabicSeeder
            seeders.append(ArabicSeeder(args.db_url))
        except ImportError:
            print("SKIP ar: seed_arabic module not yet implemented")
    if args.language in ("en", "all"):
        try:
            from .seed_english import EnglishSeeder
            seeders.append(EnglishSeeder(args.db_url))
        except ImportError:
            print("SKIP en: seed_english module not yet implemented")
    if args.language in ("sw", "all"):
        from .seed_swahili import SwahiliSeeder
        seeders.append(SwahiliSeeder(args.db_url))
    if args.language in ("tr", "all"):
        from .seed_turkish import TurkishSeeder
        seeders.append(TurkishSeeder(args.db_url))
    if args.language in ("yo", "all"):
        from .seed_yoruba import YorubaSeeder
        seeders.append(YorubaSeeder(args.db_url))
    if args.language in ("ha", "all"):
        from .seed_hausa import HausaSeeder
        seeders.append(HausaSeeder(args.db_url))
    if args.language in ("xh", "all"):
        from .seed_xhosa import XhosaSeeder
        seeders.append(XhosaSeeder(args.db_url))
    from .seed_latin import SEEDERS as LATIN_SEEDERS
    for code, seeder_cls in LATIN_SEEDERS.items():
        if args.language in (code, "all"):
            seeders.append(seeder_cls(args.db_url))

    for seeder in seeders:
        try:
            count = await seeder.run()
            print(f"OK {seeder.language_code}: {count} words loaded")
        except Exception as e:
            print(f"FAIL {seeder.language_code}: {e}")


if __name__ == "__main__":
    asyncio.run(main())
