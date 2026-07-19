"""Seed Alphabet decks for non-Latin scripts.

One studyable card per letter, at the pre-A1 level 'A0', grouped into an
"Alphabet" content_list. The card is a production drill: the prompt is the
letter's romanization + sound, and the learner types the letter (the
transliteration keyboard turns their Latin keys into the script). Idempotent.

Russian and Greek ship here — clean, unambiguous alphabets. Arabic, Hindi, and
Thai need per-letter data authored/verified by a speaker (positional forms,
matras, tone/consonant classes) and are intentionally left for a later wave.

CLI: python -m backend.services.seeder.seed_alphabet --language ru
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import os

import asyncpg

logger = logging.getLogger("seed_alphabet")

# (letter, romanization, sound-for-an-English-speaker)
RUSSIAN = [
    ("а", "a", "'a' as in father"), ("б", "b", "'b' as in boy"),
    ("в", "v", "'v' as in van"), ("г", "g", "'g' as in go"),
    ("д", "d", "'d' as in dog"), ("е", "ye", "'ye' as in yes"),
    ("ё", "yo", "'yo' as in yonder"), ("ж", "zh", "'s' in measure"),
    ("з", "z", "'z' as in zoo"), ("и", "i", "'ee' as in see"),
    ("й", "y", "short 'y' as in boy"), ("к", "k", "'k' as in kit"),
    ("л", "l", "'l' as in lamp"), ("м", "m", "'m' as in map"),
    ("н", "n", "'n' as in net"), ("о", "o", "'o' as in more"),
    ("п", "p", "'p' as in pen"), ("р", "r", "rolled 'r'"),
    ("с", "s", "'s' as in sun"), ("т", "t", "'t' as in top"),
    ("у", "u", "'oo' as in boot"), ("ф", "f", "'f' as in fan"),
    ("х", "kh", "'ch' in Scottish loch"), ("ц", "ts", "'ts' as in cats"),
    ("ч", "ch", "'ch' as in chip"), ("ш", "sh", "'sh' as in shoe"),
    ("щ", "shch", "a long, soft 'sh'"), ("ъ", "–", "hard sign — no sound of its own"),
    ("ы", "y", "a dull 'ih', tongue pulled back"), ("ь", "'", "soft sign — softens the letter before it"),
    ("э", "e", "'e' as in met"), ("ю", "yu", "'yu' as in universe"),
    ("я", "ya", "'ya' as in yard"),
]

GREEK = [
    ("α", "a", "'a' as in father"), ("β", "v", "'v' as in van"),
    ("γ", "g", "soft 'gh'; 'y' before e/i"), ("δ", "d", "'th' as in this"),
    ("ε", "e", "'e' as in met"), ("ζ", "z", "'z' as in zoo"),
    ("η", "i", "'ee' as in see"), ("θ", "th", "'th' as in thin"),
    ("ι", "i", "'ee' as in see"), ("κ", "k", "'k' as in kit"),
    ("λ", "l", "'l' as in lamp"), ("μ", "m", "'m' as in map"),
    ("ν", "n", "'n' as in net"), ("ξ", "x", "'x' as in box"),
    ("ο", "o", "'o' as in got"), ("π", "p", "'p' as in pen"),
    ("ρ", "r", "rolled 'r'"), ("σ", "s", "'s' as in sun (final form: ς)"),
    ("τ", "t", "'t' as in top"), ("υ", "y", "'ee' as in see"),
    ("φ", "f", "'f' as in fan"), ("χ", "ch", "'ch' in Scottish loch"),
    ("ψ", "ps", "'ps' as in lapse"), ("ω", "o", "'o' as in got"),
]

ALPHABETS: dict[str, list[tuple[str, str, str]]] = {"ru": RUSSIAN, "el": GREEK}


async def seed(db_url: str, code: str) -> int:
    letters = ALPHABETS.get(code)
    if not letters:
        logger.warning("no alphabet data for %s (ru, el available)", code)
        return 0
    conn = await asyncpg.connect(db_url)
    try:
        lang_id = await conn.fetchval("SELECT id FROM languages WHERE code = $1", code)
        if not lang_id:
            raise ValueError(f"language '{code}' not found")
        # The Alphabet deck: a pre-A1 vocabulary list, ordered before everything.
        await conn.execute(
            """
            INSERT INTO content_lists (language_id, list_type, level, title,
                                       description, display_order)
            VALUES ($1, 'vocabulary', 'A0', 'Alphabet',
                    'Learn to read the script — one letter at a time.', -1)
            ON CONFLICT (language_id, list_type, level)
                DO UPDATE SET title = EXCLUDED.title,
                             description = EXCLUDED.description,
                             display_order = EXCLUDED.display_order
            """,
            lang_id,
        )
        n = 0
        for rank, (letter, rom, sound) in enumerate(letters, start=1):
            vid = await conn.fetchval(
                """
                INSERT INTO vocabulary (language_id, word, reading,
                                        part_of_speech, level, frequency_rank)
                VALUES ($1, $2, $3, 'letter', 'A0', $4)
                ON CONFLICT (language_id, word)
                    DO UPDATE SET reading = EXCLUDED.reading,
                                 part_of_speech = 'letter',
                                 level = 'A0',
                                 frequency_rank = EXCLUDED.frequency_rank
                RETURNING id
                """,
                lang_id, letter, rom, rank,
            )
            await conn.execute(
                """
                INSERT INTO translations (vocabulary_id, locale, definition)
                VALUES ($1, 'en', $2)
                ON CONFLICT (vocabulary_id, locale)
                    DO UPDATE SET definition = EXCLUDED.definition
                """,
                vid, f"{rom} — {sound}",
            )
            n += 1
        logger.info("OK %s: seeded %d letters", code, n)
        return n
    finally:
        await conn.close()


async def main() -> None:
    p = argparse.ArgumentParser(description="Seed an Alphabet deck")
    p.add_argument("--language", "-l", required=True, choices=sorted(ALPHABETS))
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return
    n = await seed(args.db_url, args.language)
    print(f"OK {args.language}: {n} letters")


if __name__ == "__main__":
    asyncio.run(main())
