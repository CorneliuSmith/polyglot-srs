"""Is the wrong language actually being STORED, or just served?

A cousin reported the Spanish course showing him Arabic translations. He is
a brand-new user, which rules out the obvious explanation: a new profile has
support_locale NULL, and `cards.py _effective_locale` maps that to English.
So either something wrote Arabic into a row that every learner reads as
English, or the report was about something else.

Reading the code cannot answer that. Every card query filters
`translation_locale` correctly and every overlay join carries `AND
locale = $n`; the repo's Spanish data files contain no Arabic at all. The
remaining place the answer can live is the database, and only the running
deployment has that.

So this asks the database two questions:

  --user EMAIL   what locale is this account actually configured for?
                 (support_locale, ui_language, the active course)
  (default)      which stored rows are written in a script that does not
                 match the locale they are filed under?

The second is the one that would explain a new user seeing Arabic: a row
with translation_locale='en' whose text is Arabic is served to EVERYONE as
English, regardless of profile. Nothing in the app would flag it, because
the label says 'en' and the label is what every query trusts.

Read-only. It writes nothing, and it needs no API key.

    python -m backend.services.quality.audit_locale_rows --user them@example.com
    python -m backend.services.quality.audit_locale_rows
    python -m backend.services.quality.audit_locale_rows --language es --limit 50
"""
from __future__ import annotations

import argparse
import asyncio
import os
import unicodedata

import asyncpg

from backend.services.locale_guard import (
    has_letters,
    probable_latin_language,
    script_of,
    script_ratio,
)

# Scripts we can positively identify. A locale whose script isn't here (any
# Latin-written language) can't be judged this way — the guard is one-sided
# by design, and says so rather than inventing a verdict.
_JUDGEABLE = (
    "ARABIC", "HEBREW", "CYRILLIC", "GREEK", "DEVANAGARI",
    "THAI", "HANGUL", "CJK", "HIRAGANA", "ARMENIAN", "GEORGIAN",
    "ETHIOPIC", "BENGALI", "TAMIL", "TELUGU",
)
_MIN = 0.25


def foreign_script(text: str, locale: str) -> str | None:
    """The script this text is really in, when it isn't the locale's.

    Returns None when the text is fine, unjudgeable, or has no letters at
    all ("1991", "—"). A Latin-script locale is judged only against the
    non-Latin scripts: we can prove "this is Arabic", never "this is
    Spanish rather than Italian".
    """
    if not text or not has_letters(text):
        return None
    expected = script_of(locale)
    if expected and script_ratio(text, expected) >= _MIN:
        return None
    for script in _JUDGEABLE:
        if script == expected:
            continue
        if script_ratio(text, script) >= _MIN:
            return script
    return None


async def check_user(conn, email: str) -> None:
    row = await conn.fetchrow(
        """
        SELECT u.email, p.support_locale, p.ui_language,
               l.code AS active_code, l.name AS active_name
        FROM auth.users u
        LEFT JOIN user_profiles p ON p.id = u.id
        LEFT JOIN languages l ON l.id = p.active_language_id
        WHERE lower(u.email) = lower($1)
        """,
        email,
    )
    if not row:
        print(f"no such account: {email}")
        return
    support = row["support_locale"]
    print(f"account:        {row['email']}")
    print(f"support_locale: {support!r}")
    print(f"ui_language:    {row['ui_language']!r}")
    print(f"active course:  {row['active_code']} ({row['active_name']})")
    # This mirrors cards.py _effective_locale exactly; if they ever diverge
    # this report becomes a lie, which is worse than not having it.
    effective = support if support and support != "en" else "en"
    print(f"\ncards render in: {effective}")
    if effective == "en":
        print("  → English. A non-English card for this account is NOT the "
              "profile's doing; check the content scan below.")
    else:
        print(f"  → {effective}. This account IS configured for non-English "
              "content. Setting the translations language back to English "
              "(Settings, or the picker in a session) clears it.")


def _foreign_latin(text: str | None) -> str | None:
    """"looks like Spanish", for a column that is supposed to be English.

    `foreign_script` can only prove a text is Arabic, Cyrillic or Greek —
    it is blind between two Latin alphabets, which is exactly where the
    last one of these hid. Conservative on purpose (see locale_guard): it
    names a language only when the closed-class function words say so, so
    this reports rows worth reading rather than every terse note.
    """
    lang = probable_latin_language(text)
    return f"looks like {lang}" if lang else None


async def scan_content(conn, code: str | None, limit: int) -> int:
    """Rows whose text is in a different script from the locale they claim."""
    langs = await conn.fetch(
        "SELECT id, code, name FROM languages"
        + (" WHERE code = $1" if code else "")
        + " ORDER BY code",
        *([code] if code else []),
    )
    total = 0
    for lang in langs:
        findings: list[tuple[str, str, str, str]] = []

        for r in await conn.fetch(
            """
            SELECT id, translation_locale AS locale, translation AS text
            FROM example_sentences
            WHERE language_id = $1 AND translation IS NOT NULL
            LIMIT $2
            """,
            lang["id"], limit,
        ):
            bad = foreign_script(r["text"], r["locale"])
            if not bad and r["locale"] == "en":
                # The Latin-to-Latin case the script test cannot reach: a
                # SPANISH row filed as 'en' is served to every learner as
                # the English fallback, and reads as English to every other
                # check in this file. That is how "El bebé llora mucho por
                # la noche." reached an Arabic-support account (6 Sep 2026).
                bad = _foreign_latin(r["text"])
            if bad:
                findings.append(("example_sentences", str(r["id"]),
                                 f"locale={r['locale']} but {bad}", r["text"]))

        for r in await conn.fetch(
            """
            SELECT ds.id, ds.translation AS text
            FROM drill_sentences ds
            JOIN grammar_points gp ON gp.id = ds.grammar_point_id
            WHERE gp.language_id = $1 AND ds.translation IS NOT NULL
            LIMIT $2
            """,
            lang["id"], limit,
        ):
            # A drill's translation column has no locale label: it IS the
            # English, by definition. Anything non-Latin in it reaches every
            # learner of this course whatever their profile says.
            bad = foreign_script(r["text"], "en") or _foreign_latin(r["text"])
            if bad:
                findings.append(("drill_sentences", str(r["id"]),
                                 f"English column but {bad}", r["text"]))

        for r in await conn.fetch(
            """
            SELECT t.vocabulary_id AS id, t.locale, t.definition AS text
            FROM translations t
            JOIN vocabulary v ON v.id = t.vocabulary_id
            WHERE v.language_id = $1 LIMIT $2
            """,
            lang["id"], limit,
        ):
            bad = foreign_script(r["text"], r["locale"])
            if bad:
                findings.append(("translations", str(r["id"]),
                                 f"locale={r['locale']} but {bad}", r["text"]))

        if findings:
            total += len(findings)
            print(f"\n=== {lang['code']} ({lang['name']}): "
                  f"{len(findings)} mislabelled ===")
            for table, rid, why, text in findings[:10]:
                print(f"  {table} {rid}\n    {why}\n    {text[:80]}")
            if len(findings) > 10:
                print(f"  … and {len(findings) - 10} more")
    return total


# ---------------------------------------------------------------------------
# An Arabic gloss that is a noun where the card needs a verb
# ---------------------------------------------------------------------------

_AR_MARKS = set("\u064B\u064C\u064D\u064E\u064F\u0650\u0651\u0652\u0670\u0640")
_TA_MARBUTA = "\u0629"
# An English gerund is CORRECTLY glossed by an Arabic masdar, and so is a
# Spanish or Turkish infinitive headword; those are not defects.
_GERUND = ("ing",)


def _ar_head(gloss: str) -> str:
    """The first orthographic word of an Arabic gloss, bared of its marks.

    The head is what carries the word class. Scanning the whole string
    instead reads the object inside a verb phrase — `يُلقي نظرة` ("throws a
    glance") tripped the ta-marbuta test on `نظرة`, which is the noun the
    verb governs. That single mistake was 22 of 120 false alarms.
    """
    s = "".join(c for c in unicodedata.normalize("NFC", gloss or "")
                if c not in _AR_MARKS).strip()
    return s.split()[0] if s else ""


def _en_definition_is_verbal(definition: str | None) -> bool:
    """Does the row's own definition describe an action rather than a thing?

    A row tagged `verb` whose definition opens "a broad-billed waterfowl"
    is a mis-tagged part of speech, not a bad gloss — a different defect,
    and not this scan's business to report.
    """
    words = (definition or "").strip().lower().split()
    return bool(words) and words[0] not in {
        "a", "an", "the", "someone", "something", "one", "any"}


def nominal_gloss_on_a_verb(word: str, pos: str | None,
                            definition: str | None, gloss: str) -> str | None:
    """Why this Arabic gloss looks like a noun on a verb row, or None.

    `translate.maker_system` asks the model for "the single word or short
    phrase a native speaker would use for THAT specific sense … Match the
    part of speech", so a noun on a verb row breaks the contract the gloss
    was written under. Measured 18 Sep 2026 against 120 flagged rows judged
    one by one: **76% precision, 86% recall** on the rows this keeps.

    Report-only at that precision. The three exclusions below are each a
    measured false-alarm class, not a guess:

    * A head beginning with a WRITTEN hamza (أ إ آ) is a form IV verb —
      `أَلْقَى`. Baring the marks turns it into `القى`, which reads as the
      definite article and is not one.
      This does **not** catch hamzat wasl, which is written as a bare alif:
      `اِلْتَهَمَ` ("devoured") bares to `التهم` and is still reported. A
      form VIII verb and `ال` + noun are the same five letters, and telling
      them apart needs a morphological analyser rather than a pattern —
      camel-tools is on the server, not here. It is counted in the 24% the
      measurement already charges against this rule.
    * An `-ing` headword is correctly glossed by a masdar.
    * A definition that opens like a noun phrase means the part-of-speech
      tag is wrong, not the gloss.

    What still slips through: a participle glossing a participle
    (`مُنْتَظِر` for "esperando"), which is the right answer in a language
    whose participles are formally nouns; and the hamzat-wasl verbs above.
    """
    if (pos or "") != "verb":
        return None
    head = _ar_head(gloss)
    if not head:
        return None
    if head[:1] in "أإآ":
        return None
    if word.endswith(_GERUND):
        return None
    if not _en_definition_is_verbal(definition):
        return None
    if head.startswith("ال"):
        return "definite article on a verb row"
    if head.endswith(_TA_MARBUTA):
        return "ta marbuta on a verb row"
    if head.startswith("م") and len(head) >= 4:
        return "mim-initial noun on a verb row"
    return None


async def scan_verb_glosses(conn, code: str | None, limit: int) -> int:
    """Verb rows whose Arabic gloss is nominal. Read-only."""
    rows = await conn.fetch(
        """
        SELECT l.code AS course, v.word, v.frequency_rank AS rank,
               v.part_of_speech AS pos, te.definition AS en_def,
               ta.definition AS ar_def
        FROM vocabulary v
        JOIN languages l ON l.id = v.language_id
        JOIN translations ta ON ta.vocabulary_id = v.id AND ta.locale = 'ar'
        LEFT JOIN translations te ON te.vocabulary_id = v.id AND te.locale = 'en'
        WHERE v.retired_at IS NULL AND COALESCE(ta.definition, '') <> ''
          AND v.part_of_speech = 'verb'
        """ + ("  AND l.code = $1" if code else "") + """
        ORDER BY v.frequency_rank NULLS LAST
        LIMIT """ + str(int(limit)),
        *([code] if code else []),
    )
    hits = []
    for r in rows:
        why = nominal_gloss_on_a_verb(r["word"], r["pos"], r["en_def"],
                                      r["ar_def"])
        if why:
            hits.append((r, why))
    if hits:
        print(f"\n=== Arabic glosses that are nouns on a verb row: {len(hits)} "
              f"of {len(rows)} verb rows scanned ===")
        print("    report-only: 76% precision measured 18 Sep 2026 "
              "(docs/quality/en-sense-ar-gloss-2026-09-18.md)")
        for r, why in hits[:15]:
            print(f"  {r['course']} {r['word']} (rank {r['rank']}) — {why}")
            print(f"    EN {(r['en_def'] or '')[:70]}")
            print(f"    AR {r['ar_def'][:40]}")
        if len(hits) > 15:
            print(f"  … and {len(hits) - 15} more")
    return len(hits)


async def main() -> None:
    p = argparse.ArgumentParser(
        description="Find content stored under the wrong language label")
    p.add_argument("--user", metavar="EMAIL",
                   help="report one account's effective content locale")
    p.add_argument("--language", "-l", help="scan one course only")
    p.add_argument("--verb-glosses", action="store_true",
                   help="also scan for Arabic glosses that are nouns on a "
                        "verb row (report-only, 76%% precision)")
    p.add_argument("--limit", type=int, default=5000,
                   help="rows per table per language (default 5000)")
    p.add_argument("--db-url", default=os.environ.get("DATABASE_URL"))
    args = p.parse_args()

    if not args.db_url:
        print("ERROR: DATABASE_URL not set.")
        return
    conn = await asyncpg.connect(args.db_url)
    try:
        if args.user:
            await check_user(conn, args.user)
            print()
        total = await scan_content(conn, args.language, args.limit)
        print(f"\nTOTAL rows in the wrong script: {total}")
        if args.verb_glosses:
            n = await scan_verb_glosses(conn, args.language, args.limit)
            print(f"\nTOTAL nominal glosses on a verb row: {n} "
                  "(report-only — about a quarter are false alarms)")
        if not total:
            print("Nothing is stored under the wrong label. If a learner "
                  "still sees another language, it is their profile's "
                  "support_locale — run with --user to confirm.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
