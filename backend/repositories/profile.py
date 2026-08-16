"""The one rule for which language a learner reads HELP in.

Glosses, drill translations, tutor explanations, Speak's correction notes,
reader glosses, gym labels — all of it renders in the *support* language,
and before this module each surface derived that language its own way. The
visible failure: the interface in English while Speak coached in French,
because two different fields both claimed to be "the user's language" and
had drifted.

The rule, stated once:

    explicit choice  →  support_locale   (set in Settings; survives
                                          everything, including the globe)
    otherwise        →  ui_language      (automatic: help follows the
                                          interface, with no stored state
                                          to go stale)
    'en' / nothing   →  None             (English — the authored source,
                                          nothing to translate)

`support_locale` therefore stores ONLY explicit decisions and NULL means
automatic. It must never be written as a side effect of changing the
interface language — that is precisely the freeze this module exists to
end: the globe used to materialize the automatic case into a stored
"choice", after which switching the interface back left the old value
overriding forever.

Every reader — request paths and the auto-translate loop's scans alike —
must go through this module. A scan that filters on the raw column while
readiness coalesces would tell one learner their session is coming in
French while stocking it in nothing.
"""
from __future__ import annotations

import asyncpg


def effective_support_sql(alias: str = "user_profiles") -> str:
    """The rule as a SQL expression, for queries that scan many profiles.

    NULLIF folds an explicitly-stored 'en' into the same shape as NULL
    ui_language handling downstream: callers compare the result against
    'en' themselves where they need to (English is the authored source and
    is never swept for translation).
    """
    return f"COALESCE({alias}.support_locale, {alias}.ui_language)"


async def effective_support_locale(
    conn: asyncpg.Connection, user_id: str
) -> str | None:
    """The learner's effective support locale, or None for English.

    None (not 'en') for the English case, matching the convention every
    existing caller already speaks: "no locale" and "English" are the same
    fact — the content's authored language needs no overlay.
    """
    row = await conn.fetchrow(
        "SELECT support_locale, ui_language FROM user_profiles WHERE id = $1",
        user_id,
    )
    if not row:
        return None
    code = row["support_locale"] or row["ui_language"]
    return code if code and code != "en" else None
