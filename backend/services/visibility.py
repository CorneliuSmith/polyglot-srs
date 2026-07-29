"""What a learner is allowed to see — one definition, used everywhere.

The rule used to be copy-pasted into 21 SQL queries as a hardcoded
`reviewed = true OR (policy = 'ai_ok' AND ai_check_status = 'pass')`. That is
why the owner could flip a language to "Open", see nothing appear, and find
nothing in the UI explaining it: the policy was only ever HALF the gate, the
other half was a per-point verdict, and neither the code nor the panel said
so anywhere a person would look.

Content carries two INDEPENDENT review signals:

    reviewed         bool    a human signed off
    ai_check_status  text    'pass' | 'concerns' | NULL (never checked)

which gives six real states, and different projects want the line drawn in
different places. So the line is a per-language setting an admin picks:

    human_only  a human approved it                    (was called 'strict')
    ai_ok       a human approved it OR an AI passed it  (the old 'ai_ok')
    both        a human approved it AND an AI passed it (belt and braces)
    all         everything, including never-checked     (preview / beta)

STAFF ARE NOT LEARNERS. Reviewers, contributors and admins see content their
learners cannot, because that is the entire point of having reviewers: work
lands, staff look at it, and only then is it promoted. Passing
`staff=True` into the clause below lifts the gate for exactly that reason.
"""
from __future__ import annotations

# Ordered weakest-gate-last, which is also the order the admin picker shows.
PUBLISH_POLICIES = ("human_only", "ai_ok", "both", "all")

#: The original name for human_only. Rows created before the four-way policy
#: still carry it, and an admin who never touches the setting keeps it, so it
#: must stay readable forever — normalise, never migrate-and-forget.
LEGACY_ALIASES = {"strict": "human_only"}

POLICY_LABELS = {
    "human_only": "Human-reviewed only",
    "ai_ok": "Human-reviewed or AI-verified",
    "both": "Human-reviewed and AI-verified",
    "all": "Everything, including unchecked",
}

POLICY_HELP = {
    "human_only": (
        "Learners see only what a person has approved. The safest setting, "
        "and the slowest to fill out a new language."
    ),
    "ai_ok": (
        "Learners also see content the automated check has passed. Content "
        "that has never been checked stays hidden."
    ),
    "both": (
        "Learners see only content that has passed the automated check AND "
        "been approved by a person."
    ),
    "all": (
        "Learners see everything, including content nothing has checked yet. "
        "Use while building a language out; expect rough edges to be visible."
    ),
}


def normalize_policy(value: str | None) -> str:
    """Map a stored value to one of PUBLISH_POLICIES.

    Anything unrecognised becomes the STRICTEST setting. A typo or a value
    from a newer deploy must never accidentally publish unreviewed content —
    failing closed is the only safe direction for a visibility gate.
    """
    if not value:
        return "human_only"
    value = LEGACY_ALIASES.get(value, value)
    return value if value in PUBLISH_POLICIES else "human_only"


def grammar_visible_sql(
    *, point: str = "gp", lang: str = "l", staff_param: str | None = None
) -> str:
    """SQL boolean: may this grammar point be shown?

    *point* and *lang* are the table aliases in the calling query. When
    *staff_param* is given (e.g. "$3"), that parameter lifts the gate
    entirely — staff reviewing content must be able to see it before their
    learners can.
    """
    gate = (
        f"CASE {lang}.grammar_review_policy"
        f" WHEN 'all' THEN true"
        f" WHEN 'both' THEN ({point}.reviewed AND {point}.ai_check_status = 'pass')"
        f" WHEN 'ai_ok' THEN ({point}.reviewed OR {point}.ai_check_status = 'pass')"
        # human_only, the legacy 'strict', and anything unknown: fail closed.
        f" ELSE {point}.reviewed END"
    )
    return f"({staff_param} OR {gate})" if staff_param else f"({gate})"


#: Policies under which content NOTHING has human-approved may still reach a
#: learner. Used by the gates on example sentences, generated drills and
#: AI-estimated vocabulary levels, which carry no per-row AI verdict of their
#: own — for those the question is only "does this language let AI content
#: through at all?".
AI_CONTENT_POLICIES = ("ai_ok", "all")

AI_CONTENT_SQL = "grammar_review_policy IN ('ai_ok', 'all')"


def lets_ai_content_through(policy: str | None) -> bool:
    return normalize_policy(policy) in AI_CONTENT_POLICIES
