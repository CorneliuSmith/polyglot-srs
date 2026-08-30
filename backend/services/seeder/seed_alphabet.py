"""Seed Alphabet decks for non-Latin scripts.

One studyable card per letter, at the pre-A1 level 'A0', grouped into an
"Alphabet" content_list. The card is a production drill: the prompt is the
letter's romanization + sound, and the learner types the letter (the
transliteration keyboard turns their Latin keys into the script). Idempotent.

All eight non-Latin courses ship a deck: ru, el, ar, hi, th, ko, he, fa.
Romanizations follow the app's own typing scheme (translit.ts) wherever the
scheme can produce the letter, so the card's prompt doubles as the key to
type; letters the scheme can't reach (Persian's borrowed ث ص ض ظ ط ح غ)
are typed on the on-screen keyboard.

CLI: python -m backend.services.seeder.seed_alphabet --language ru
"""
from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os

import asyncpg

from .base import DATA_DIR

logger = logging.getLogger("seed_alphabet")

# An extractor (extra-agent) can drop a data/alphabet/{code}.json artifact —
# {"language": code, "letters": [{"letter", "romanization", "sound"}]} — for a
# script we don't ship hardcoded. When present it takes precedence, so a
# speaker-reviewed alphabet from a document seeds without touching this file.
ALPHABET_DIR = DATA_DIR / "alphabet"


def _load_file_alphabet(code: str) -> list[tuple[str, str, str]] | None:
    path = ALPHABET_DIR / f"{code}.json"
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    letters: list[tuple[str, str, str]] = []
    for e in data.get("letters", []):
        letter = str(e.get("letter") or "").strip()
        rom = str(e.get("romanization") or "").strip()
        sound = str(e.get("sound") or "").strip()
        if letter:
            letters.append((letter, rom, sound))
    return letters or None

# (letter, romanization, sound-for-an-English-speaker)
# The romanization is the TYPING KEY: what the learner types on the QWERTY
# transliteration keyboard to produce the letter. A letter card whose shown
# key produces a different letter (Greek η labeled "i" — but i types ι) is
# a card the learner cannot pass; the typing scheme, not a scholarly
# romanization standard, is the source of truth here.
RUSSIAN = [
    ("а", "a", "'a' as in father"), ("б", "b", "'b' as in boy"),
    ("в", "v", "'v' as in van"), ("г", "g", "'g' as in go"),
    ("д", "d", "'d' as in dog"), ("е", "ye", "'ye' as in yes"),
    ("ё", "yo", "'yo' as in yonder"), ("ж", "zh", "'s' in measure"),
    ("з", "z", "'z' as in zoo"), ("и", "i", "'ee' as in see"),
    ("й", "j", "short 'y' as in boy"), ("к", "k", "'k' as in kit"),
    ("л", "l", "'l' as in lamp"), ("м", "m", "'m' as in map"),
    ("н", "n", "'n' as in net"), ("о", "o", "'o' as in more"),
    ("п", "p", "'p' as in pen"), ("р", "r", "rolled 'r'"),
    ("с", "s", "'s' as in sun"), ("т", "t", "'t' as in top"),
    ("у", "u", "'oo' as in boot"), ("ф", "f", "'f' as in fan"),
    ("х", "kh", "'ch' in Scottish loch"), ("ц", "ts", "'ts' as in cats"),
    ("ч", "ch", "'ch' as in chip"), ("ш", "sh", "'sh' as in shoe"),
    ("щ", "shch", "a long, soft 'sh'"), ("ъ", "''", "hard sign — no sound of its own"),
    ("ы", "y", "a dull 'ih', tongue pulled back"), ("ь", "'", "soft sign — softens the letter before it"),
    ("э", "e'", "'e' as in met"), ("ю", "yu", "'yu' as in universe"),
    ("я", "ya", "'ya' as in yard"),
]

GREEK = [
    ("α", "a", "'a' as in father"), ("β", "v", "'v' as in van"),
    ("γ", "g", "soft 'gh'; 'y' before e/i"), ("δ", "d", "'th' as in this"),
    ("ε", "e", "'e' as in met"), ("ζ", "z", "'z' as in zoo"),
    ("η", "h", "'ee' as in see"), ("θ", "th", "'th' as in thin"),
    ("ι", "i", "'ee' as in see"), ("κ", "k", "'k' as in kit"),
    ("λ", "l", "'l' as in lamp"), ("μ", "m", "'m' as in map"),
    ("ν", "n", "'n' as in net"), ("ξ", "x", "'x' as in box"),
    ("ο", "o", "'o' as in got"), ("π", "p", "'p' as in pen"),
    ("ρ", "r", "rolled 'r'"), ("σ", "s", "'s' as in sun (final form: ς)"),
    ("τ", "t", "'t' as in top"), ("υ", "y", "'ee' as in see"),
    ("φ", "f", "'f' as in fan"), ("χ", "ch", "'ch' in Scottish loch"),
    ("ψ", "ps", "'ps' as in lapse"), ("ω", "w", "'o' as in got"),
]

ARABIC = [
    ("ا", "aa", "long 'aa', or a seat for other vowels"),
    ("ب", "b", "'b' as in boy"), ("ت", "t", "'t' as in top"),
    ("ث", "th", "'th' as in think"), ("ج", "j", "'j' as in jam"),
    ("ح", "H", "a breathy 'h' from deep in the throat (also typed 7)"),
    ("خ", "kh", "'ch' as in Scottish loch"), ("د", "d", "'d' as in dog"),
    ("ذ", "dh", "'th' as in this"), ("ر", "r", "a rolled 'r'"),
    ("ز", "z", "'z' as in zoo"), ("س", "s", "'s' as in sun"),
    ("ش", "sh", "'sh' as in shoe"), ("ص", "S", "a heavy, deep 's'"),
    ("ض", "D", "a heavy, deep 'd'"), ("ط", "T", "a heavy, deep 't'"),
    ("ظ", "Z", "a heavy, deep 'dh'"),
    ("ع", "3", "a tight sound from the throat — no English match"),
    ("غ", "gh", "a gargled 'r', like a French 'r'"), ("ف", "f", "'f' as in fan"),
    ("ق", "q", "a 'k' made far back in the throat"), ("ك", "k", "'k' as in kit"),
    ("ل", "l", "'l' as in lamp"), ("م", "m", "'m' as in map"),
    ("ن", "n", "'n' as in net"), ("ه", "h", "'h' as in hat"),
    ("و", "w", "'w' as in wet, or a long 'oo'"),
    ("ي", "y", "'y' as in yes, or a long 'ee'"),
]

# Hindi (Devanagari): vowels first, then the consonant series. Consonants
# carry the inherent 'a', so क is "ka".
HINDI = [
    ("अ", "a", "short 'a' as in about"), ("आ", "aa", "long 'aa' as in father"),
    ("इ", "i", "short 'i' as in sit"), ("ई", "ii", "long 'ee' as in see"),
    ("उ", "u", "short 'u' as in put"), ("ऊ", "uu", "long 'oo' as in boot"),
    ("ए", "e", "'ay' as in say"), ("ऐ", "ai", "'ai' as in aisle"),
    ("ओ", "o", "'o' as in go"), ("औ", "au", "'au' as in caught"),
    ("क", "ka", "'k' as in skate"), ("ख", "kha", "aspirated 'k' — k with a puff"),
    ("ग", "ga", "'g' as in go"), ("घ", "gha", "aspirated 'g'"),
    ("ङ", "nga", "'ng' as in sing"), ("च", "cha", "'ch' as in church"),
    ("छ", "chha", "aspirated 'ch'"), ("ज", "ja", "'j' as in jam"),
    ("झ", "jha", "aspirated 'j'"), ("ञ", "nya", "'ny' as in canyon"),
    ("ट", "Ta", "hard 't', tongue curled back"), ("ठ", "Tha", "aspirated hard 't'"),
    ("ड", "Da", "hard 'd', tongue curled back"), ("ढ", "Dha", "aspirated hard 'd'"),
    ("ण", "Na", "hard 'n', tongue curled back"), ("त", "ta", "soft 't', tongue on teeth"),
    ("थ", "tha", "aspirated soft 't'"), ("द", "da", "soft 'd', tongue on teeth"),
    ("ध", "dha", "aspirated soft 'd'"), ("न", "na", "'n' as in net"),
    ("प", "pa", "'p' as in spin"), ("फ", "pha", "aspirated 'p'"),
    ("ब", "ba", "'b' as in boy"), ("भ", "bha", "aspirated 'b'"),
    ("म", "ma", "'m' as in map"), ("य", "ya", "'y' as in yes"),
    ("र", "ra", "a rolled 'r'"), ("ल", "la", "'l' as in lamp"),
    ("व", "va", "between 'v' and 'w'"), ("श", "sha", "'sh' as in shoe"),
    ("ष", "Sha", "hard 'sh', tongue curled back"), ("स", "sa", "'s' as in sun"),
    ("ह", "ha", "'h' as in hat"),
]

# Thai consonants (44). The romanization is the INITIAL sound; the class
# (low/mid/high) that decides the tone is noted, since it's the thing a
# beginner needs alongside the shape.
THAI = [
    ("ก", "k", "'g' as in go (mid class)"), ("ข", "kh", "'k' with a puff (high class)"),
    ("ฃ", "kh", "'k' with a puff — obsolete (high class)"),
    ("ค", "kh", "'k' with a puff (low class)"),
    ("ฅ", "kh", "'k' with a puff — obsolete (low class)"),
    ("ฆ", "kh", "'k' with a puff (low class)"), ("ง", "ng", "'ng' as in sing (low class)"),
    ("จ", "j", "'j' as in jar (mid class)"), ("ฉ", "ch", "'ch' with a puff (high class)"),
    ("ช", "ch", "'ch' (low class)"), ("ซ", "s", "'s' as in sun (low class)"),
    ("ฌ", "ch", "'ch' (low class)"), ("ญ", "y", "'y' as in yes (low class)"),
    ("ฎ", "d", "'d' as in dog (mid class)"), ("ฏ", "t", "hard 't' (mid class)"),
    ("ฐ", "th", "'t' with a puff (high class)"), ("ฑ", "th", "'t' with a puff (low class)"),
    ("ฒ", "th", "'t' with a puff (low class)"), ("ณ", "n", "'n' as in net (low class)"),
    ("ด", "d", "'d' as in dog (mid class)"), ("ต", "t", "hard 't' (mid class)"),
    ("ถ", "th", "'t' with a puff (high class)"), ("ท", "th", "'t' with a puff (low class)"),
    ("ธ", "th", "'t' with a puff (low class)"), ("น", "n", "'n' as in net (low class)"),
    ("บ", "b", "'b' as in boy (mid class)"), ("ป", "p", "'p' as in spin (mid class)"),
    ("ผ", "ph", "'p' with a puff (high class)"), ("ฝ", "f", "'f' as in fan (high class)"),
    ("พ", "ph", "'p' with a puff (low class)"), ("ฟ", "f", "'f' as in fan (low class)"),
    ("ภ", "ph", "'p' with a puff (low class)"), ("ม", "m", "'m' as in map (low class)"),
    ("ย", "y", "'y' as in yes (low class)"), ("ร", "r", "a rolled 'r' (low class)"),
    ("ล", "l", "'l' as in lamp (low class)"), ("ว", "w", "'w' as in we (low class)"),
    ("ศ", "s", "'s' as in sun (high class)"), ("ษ", "s", "'s' as in sun (high class)"),
    ("ส", "s", "'s' as in sun (high class)"), ("ห", "h", "'h' as in hat (high class)"),
    ("ฬ", "l", "'l' as in lamp (low class)"),
    ("อ", "-", "silent holder for a vowel (mid class)"),
    ("ฮ", "h", "'h' as in hat (low class)"),
]

# Hangul jamo (WP27). Consonants first (plain, aspirated, tense), then
# vowels — the block-assembly rule lives in the Letters & Sounds panel;
# the deck drills each letter's sound.
HANGUL = [
    ("ㄱ", "g", "between 'g' and 'k'"), ("ㄴ", "n", "'n' as in no"),
    ("ㄷ", "d", "between 'd' and 't'"), ("ㄹ", "r", "a tap 'r'; 'l' at the end of a block"),
    ("ㅁ", "m", "'m' as in mom"), ("ㅂ", "b", "between 'b' and 'p'"),
    ("ㅅ", "s", "'s' as in see; 'sh' before ㅣ"),
    ("ㅇ", "ng", "silent at the start; 'ng' at the end"),
    ("ㅈ", "j", "between 'j' and 'ch'"), ("ㅎ", "h", "'h' as in hat"),
    ("ㅋ", "k", "'k' with a strong puff"), ("ㅌ", "t", "'t' with a strong puff"),
    ("ㅍ", "p", "'p' with a strong puff"), ("ㅊ", "ch", "'ch' with a strong puff"),
    ("ㄲ", "kk", "a tight 'k', no puff"), ("ㄸ", "tt", "a tight 't', no puff"),
    ("ㅃ", "pp", "a tight 'p', no puff"), ("ㅆ", "ss", "a tight 's'"),
    ("ㅉ", "jj", "a tight 'j', no puff"),
    ("ㅏ", "a", "'ah' as in father"), ("ㅓ", "eo", "'u' as in cut — an open 'aw'"),
    ("ㅗ", "o", "'o' as in go"), ("ㅜ", "u", "'oo' as in moon"),
    ("ㅡ", "eu", "'oo' with flat lips — smile while saying it"),
    ("ㅣ", "i", "'ee' as in see"), ("ㅐ", "ae", "'e' as in bed"),
    ("ㅔ", "e", "'e' as in bed (same sound today)"),
    ("ㅑ", "ya", "'ya' as in yard"), ("ㅕ", "yeo", "'yu' as in young"),
    ("ㅛ", "yo", "'yo' as in yogurt"), ("ㅠ", "yu", "'you'"),
    ("ㅒ", "yae", "'ye' as in yes"), ("ㅖ", "ye", "'ye' as in yes"),
    ("ㅘ", "wa", "'wa' as in water"), ("ㅝ", "wo", "'wo' as in wonder"),
    ("ㅙ", "wae", "'we' as in wet"), ("ㅞ", "we", "'we' as in wet"),
    ("ㅚ", "oe", "'we' as in wet (modern speech)"), ("ㅟ", "wi", "'wee' as in week"),
    ("ㅢ", "ui", "'u'+'i' glided; often just 'i' in speech"),
]

# Hebrew alef-bet (22), then the five final forms as their own cards — the
# shape change IS the thing to learn. Romanization = the typing key.
HEBREW = [
    ("א", "a", "silent — a seat for a vowel"),
    ("ב", "b", "'b' as in boy ('v' without its dot)"),
    ("ג", "g", "'g' as in go"), ("ד", "d", "'d' as in dog"),
    ("ה", "h", "'h' as in hat; silent at a word's end"),
    ("ו", "v", "'v'; also spells long 'o'/'u'"),
    ("ז", "z", "'z' as in zoo"),
    ("ח", "ch", "'ch' as in Scottish loch"),
    ("ט", "T", "'t' as in top (same sound as ת today)"),
    ("י", "y", "'y' as in yes; also spells long 'ee'"),
    ("כ", "k", "'k'; 'kh' without its dot"),
    ("ל", "l", "'l' as in lamp"), ("מ", "m", "'m' as in map"),
    ("נ", "n", "'n' as in net"), ("ס", "s", "'s' as in sun"),
    ("ע", "'", "a catch in the throat; often silent"),
    ("פ", "p", "'p'; 'f' without its dot"),
    ("צ", "ts", "'ts' as in cats"),
    ("ק", "q", "'k' as in kit (same sound as כ today)"),
    ("ר", "r", "a gargled 'r' from the back of the throat"),
    ("ש", "sh", "'sh' as in shoe; 's' with a left dot"),
    ("ת", "t", "'t' as in top"),
    ("ך", "k", "kaf at the end of a word — same sound"),
    ("ם", "m", "mem at the end of a word — same sound"),
    ("ן", "n", "nun at the end of a word — same sound"),
    ("ף", "p", "pe at the end of a word — same sound"),
    ("ץ", "ts", "tsadi at the end of a word — same sound"),
]

# Persian (32 letters). The borrowed Arabic letters all merged into plain
# s/z/t/h — the romanization shows the SOUND; the ones the Finglish scheme
# can't reach are typed on the on-screen keyboard.
PERSIAN = [
    ("آ", "aa", "long 'aw' as in law — alef with a madda"),
    ("ا", "a", "a seat for a vowel at the start of a word"),
    ("ب", "b", "'b' as in boy"), ("پ", "p", "'p' as in pen"),
    ("ت", "t", "'t' as in top"),
    ("ث", "s", "'s' as in sun — borrowed letter, plain 's' in Persian"),
    ("ج", "j", "'j' as in jam"), ("چ", "ch", "'ch' as in chair"),
    ("ح", "h", "'h' as in hat — borrowed letter, plain 'h' in Persian"),
    ("خ", "kh", "'ch' as in Scottish loch"),
    ("د", "d", "'d' as in dog"),
    ("ذ", "z", "'z' as in zoo — borrowed letter, plain 'z' in Persian"),
    ("ر", "r", "a tapped 'r'"), ("ز", "z", "'z' as in zoo"),
    ("ژ", "zh", "'s' in measure"),
    ("س", "s", "'s' as in sun"), ("ش", "sh", "'sh' as in shoe"),
    ("ص", "s", "'s' as in sun — borrowed letter, plain 's' in Persian"),
    ("ض", "z", "'z' as in zoo — borrowed letter, plain 'z' in Persian"),
    ("ط", "t", "'t' as in top — borrowed letter, plain 't' in Persian"),
    ("ظ", "z", "'z' as in zoo — borrowed letter, plain 'z' in Persian"),
    ("ع", "'", "a slight catch in the throat; often nothing at all"),
    ("غ", "gh", "a gargled 'g', like a French 'r'"),
    ("ف", "f", "'f' as in fan"),
    ("ق", "q", "the same gargled 'g' for most speakers"),
    ("ک", "k", "'k' as in kit"), ("گ", "g", "'g' as in go"),
    ("ل", "l", "'l' as in lamp"), ("م", "m", "'m' as in map"),
    ("ن", "n", "'n' as in net"),
    ("و", "v", "'v' as in van; also spells long 'oo'/'o'"),
    ("ه", "h", "'h' as in hat"),
    ("ی", "y", "'y' as in yes; also spells long 'ee'"),
]

ALPHABETS: dict[str, list[tuple[str, str, str]]] = {
    "ru": RUSSIAN, "el": GREEK, "ar": ARABIC, "hi": HINDI, "th": THAI,
    "ko": HANGUL, "he": HEBREW, "fa": PERSIAN,
}

# Compat jamo vowels ㅏ..ㅣ (U+314F–U+3163) are exactly the 21 syllable
# medials in order; ㅇ is initial index 11 in the syllable arithmetic
# code = 0xAC00 + (initial*21 + medial)*28 + final.
_COMPAT_VOWEL_FIRST, _COMPAT_VOWEL_LAST = 0x314F, 0x3163
_SILENT_IEUNG_INITIAL = 11

# Hebrew final forms: the transliteration keyboard finalizes a lone typed
# letter to its FINAL form (k → ך), so each plain/final pair accepts the
# other — both cards stay fully typeable, and the coaching fold still names
# the proper form when it matters inside a word.
_HE_FINAL_OF = {"כ": "ך", "מ": "ם", "נ": "ן", "פ": "ף", "צ": "ץ"}
_HE_PLAIN_OF = {v: k for k, v in _HE_FINAL_OF.items()}


def _letter_alternatives(code: str, letter: str) -> list[str] | None:
    """Extra accepted spellings for a letter card, where the typing scheme
    can't produce the bare glyph.

    The Korean transliteration keyboard seats a lone vowel on silent ㅇ
    (typing "a" yields 아, never bare ㅏ) — so the vowel cards accept the
    seated syllable alongside the jamo. Hebrew plain/final pairs accept each
    other. Everything else the NLP layer already folds (ᄀ/ㄱ via NFKC, σ/ς,
    alef variants).
    """
    if code == "ko" and len(letter) == 1:
        cp = ord(letter)
        if _COMPAT_VOWEL_FIRST <= cp <= _COMPAT_VOWEL_LAST:
            medial = cp - _COMPAT_VOWEL_FIRST
            seated = chr(0xAC00 + (_SILENT_IEUNG_INITIAL * 21 + medial) * 28)
            return [seated]
    if code == "he":
        if letter in _HE_FINAL_OF:
            return [_HE_FINAL_OF[letter]]
        if letter in _HE_PLAIN_OF:
            return [_HE_PLAIN_OF[letter]]
    return None


async def seed(db_url: str, code: str) -> int:
    # A checked-in artifact wins over the hardcoded table.
    letters = _load_file_alphabet(code) or ALPHABETS.get(code)
    if not letters:
        logger.warning(
            "no alphabet data for %s (hardcoded: %s; or add data/alphabet/%s.json)",
            code, ", ".join(sorted(ALPHABETS)), code,
        )
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
                                        part_of_speech, level, frequency_rank,
                                        alternatives)
                VALUES ($1, $2, $3, 'letter', 'A0', $4, $5)
                ON CONFLICT (language_id, word)
                    DO UPDATE SET reading = EXCLUDED.reading,
                                 part_of_speech = 'letter',
                                 level = 'A0',
                                 frequency_rank = EXCLUDED.frequency_rank,
                                 alternatives = EXCLUDED.alternatives
                RETURNING id
                """,
                # `or []` because vocabulary.alternatives is NOT NULL DEFAULT
                # '{}' and an explicit NULL does NOT fall back to the default.
                # _letter_alternatives returns None for any letter with no
                # special case — which is the FIRST letter of every alphabet
                # here — so each of these seeders aborted on its opening row.
                lang_id, letter, rom, rank,
                _letter_alternatives(code, letter) or [],
            )
            await conn.execute(
                """
                INSERT INTO translations (vocabulary_id, locale, definition)
                VALUES ($1, 'en', $2)
                ON CONFLICT (vocabulary_id, locale)
                    DO UPDATE SET definition = EXCLUDED.definition
                """,
                vid, f"{rom} — {sound}" if sound else (rom or letter),
            )
            n += 1
        logger.info("OK %s: seeded %d letters", code, n)
        return n
    finally:
        await conn.close()


async def main() -> None:
    file_codes = (
        {f.stem for f in ALPHABET_DIR.glob("*.json")} if ALPHABET_DIR.exists() else set()
    )
    p = argparse.ArgumentParser(description="Seed an Alphabet deck")
    p.add_argument(
        "--language", "-l", required=True,
        choices=sorted(set(ALPHABETS) | file_codes),
    )
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
