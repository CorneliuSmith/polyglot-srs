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


async def main() -> None:
    p = argparse.ArgumentParser(
        description="Find content stored under the wrong language label")
    p.add_argument("--user", metavar="EMAIL",
                   help="report one account's effective content locale")
    p.add_argument("--language", "-l", help="scan one course only")
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
        if not total:
            print("Nothing is stored under the wrong label. If a learner "
                  "still sees another language, it is their profile's "
                  "support_locale — run with --user to confirm.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
