"""The explicit-content gate, as one clause every learner-facing read uses.

Slurs and strong profanity are frequent (Spanish *puta* is rank 505 in the
shipped list), so they reach beginners early unless filtered; the learner
preference `user_profiles.allow_explicit_content` (off by default, toggled
in Settings) decides. Two tables carry the flag: `vocabulary` (the word) and
`example_sentences` (an ordinary word can have a crude example — the corpus
attached "Fucking whore." to *maldita*, which just means "damned").

The gate started narrower — Learn and card examples only — and the first
audit found the gap that narrowness invites: a filtered learner could not be
TAUGHT "puta" but could open the A1 deck, or search for it, and read
"whore, slut, prostitute" straight off the listing. A gate that only covers
the front door is a claim, not a gate. Every query that can put a flagged
row in front of a learner routes through here now; this module exists (out
of cards.py) so curriculum.py can use it without a circular import.

Keyed on auth.uid() rather than a bind parameter: gated reads run on RLS
connections that already carry the learner's identity, and threading a user
id through six unrelated signatures to restate what the connection knows
invites exactly one caller getting it wrong. auth.uid() is provided by
Supabase and by the shim in scripts/setup_db.sh, so it works on both.

Staff surfaces (contributor editors, review queues) deliberately do NOT use
this: a reviewer deciding whether a flagged sentence should exist has to be
able to see it.
"""
from __future__ import annotations

import asyncpg

_EXPLICIT_SQL = (
    " AND (NOT {alias}is_explicit"
    "      OR EXISTS (SELECT 1 FROM user_profiles up"
    "                  WHERE up.id = auth.uid()"
    "                    AND up.allow_explicit_content))"
)


def explicit_clause(alias: str = "") -> str:
    """The gate as a SQL fragment, for the given table alias."""
    return _EXPLICIT_SQL.format(alias=f"{alias}." if alias else "")


async def fetch_explicit_gated(conn, sql: str, *args, alias: str = ""):
    """Run a query with the gate spliced in at `{explicit}`, falling back to
    the unfiltered form when migration 20260910 hasn't been applied —
    content stays reachable, the gate simply has nothing to gate yet."""
    try:
        return await conn.fetch(
            sql.replace("{explicit}", explicit_clause(alias)), *args
        )
    except asyncpg.exceptions.UndefinedColumnError:
        return await conn.fetch(sql.replace("{explicit}", ""), *args)
