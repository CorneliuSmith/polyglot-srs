"""The quality rules the generation prompts share.

One module, because the rules used to live as string fragments inside
`generate.py` and drifted: the drill and example MAKERS were told to pitch
complexity at the item's CEFR level in one wording, and the two AUDITORS
were told to judge "too simple" relative to that level in another,
independently written wording. Two descriptions of one bar is how a
sentence passes the maker and fails the auditor, or the reverse, and
nobody can say which is right (docs/plans/owner-notes-2026-09-03.md,
item 4).

What lives here:

* `DIVERSITY_RULES` — the set-level variety charter (owner's screenshot:
  six subject-pronoun drills, all "pronoun + ser + noun").
* `level_bar(level)` — ONE sentence describing what a CEFR level supports.
  `maker_complexity_rule` and `auditor_level_rule` both quote it, so the
  maker aims at exactly the bar the auditor holds.
* `language_brief(code)` — the per-language tutor brief
  (`tutor_skills/<code>/SKILL.md`), so a maker writing Arabic drills has
  the same register and dialect guidance the semantic reviewer and the
  seeders already get. It was missing from the makers and the auditors.

Not here, and not to be added: the 42-rule digest in
`.claude/skills/quality-rules/SKILL.md`. That governs the Claude Code
sessions that clean data and is the owner's judgement in prose; a runtime
prompt that read it would pay for 400 lines per call and could not be
tested. Rules move from there to here one at a time, as short mechanical
statements, when a generator needs them.
"""
from __future__ import annotations

from backend.services.tutor import _load_skill

DIVERSITY_RULES = (
    " Across the set, maximize variety: use a DIFFERENT main verb in each "
    "sentence (unless the point itself drills one specific verb), different "
    "topics (work, travel, food, family, plans, opinions, past events — not "
    "six variations of one situation), and different shapes — mix plain "
    "statements with at least one question and one negation, and vary how "
    "sentences open. Never produce a set where every sentence follows the "
    "same frame."
)


def level_bar(level: str | None) -> str:
    """What a CEFR level supports, in one sentence. Empty for no level.

    Quoted verbatim by both the maker's rule and the auditor's rule, so
    the bar a sentence is written to is the bar it is judged by.
    """
    lvl = (level or "").strip().upper()
    if not lvl:
        return ""
    if lvl in ("A1", "A2"):
        return (f"CEFR {lvl}: short, concrete sentences with everyday words "
                "and the basic tenses — but varied, since simple does not "
                "mean identical, and never a bare label or a stilted "
                "textbook line.")
    return (f"CEFR {lvl}: connectors, subordinate clauses and natural "
            "time/place detail where the level supports them — as rich as "
            "the level allows, never simpler.")


def maker_complexity_rule(level: str | None) -> str:
    """The maker's instruction: write to the bar."""
    bar = level_bar(level)
    return f" Pitch every sentence at {bar}" if bar else ""


def auditor_level_rule(level: str | None) -> str:
    """The auditor's instruction: judge against the same bar."""
    bar = level_bar(level)
    return (f" The item's level is {bar} Judge 'too simple' relative to "
            "that, not to a beginner." if bar else "")


def language_brief(language_code: str | None) -> str:
    """The per-language tutor brief as a prompt suffix, or nothing.

    SKILL.md is capped at 2,500 characters by test, so this is affordable
    per batch; it is a paragraph of register, dialect and common-error
    guidance the model would otherwise guess at.
    """
    if not language_code:
        return ""
    brief = _load_skill(language_code)
    return f"\n\nLanguage brief:\n{brief}" if brief else ""
