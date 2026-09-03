"""Central task -> model resolution (WP39).

One place that answers "which model runs this task", so model selection stops
being scattered across config defaults, per-service literals, and CLI flags.
Every AI task resolves through resolve_model(); the per-language admin override
and the low-resource pin still apply. This is also the seam the on-demand
generation (Part C) and paid ingest (Part D) plug into — their maker/checker
models live here rather than only as CLI flags.

The task -> config-field map below is the single source of truth the
.env.example sample and any future admin UI document against.
"""

from __future__ import annotations

from backend.config import get_settings

# Languages where accuracy is the differentiator — the tutor and the content
# makers pin the stronger model for these unless an admin overrides per
# language. (Kept here so tutor.py and the generators share one definition.)
LOW_RESOURCE_LANGUAGES = frozenset({"mi", "sw", "yo", "ha", "xh", "ar"})

# Task -> the Settings field holding its model. Tasks without a dedicated
# setting deliberately share one (documented here, not hidden in call sites).
#   *_maker  drafts content;  *_checker verifies it one tier up (§6: never
#   self-certify). checker defaults to the low-resource (stronger) model.
TASK_MODELS: dict[str, str] = {
    "tutor_chat": "tutor_model",
    "reader": "tutor_model",
    "tutor_summary": "tutor_summary_model",
    "semantic_check": "tutor_summary_model",
    "translate": "tutor_summary_model",
    # The locale-translation checker. It used to share "translate" with the
    # maker, so the sweep, the demand lane and the inline fill all checked
    # Sonnet with Sonnet — the one lane where the never-self-certify rule
    # above did not hold (docs/plans/owner-notes-2026-09-03.md, item 5).
    "translate_checker": "tutor_model_low_resource",
    # Weekly immersion recommendations: reasoning + real-world knowledge matter,
    # so it rides the stronger chat model.
    "recommend": "tutor_model",
    # CEFR level estimation for un-ranked vocab: a judgement call, pinned strong
    # on low-resource languages where the model is least reliable.
    "level_estimate": "tutor_model",
    "grammar_maker": "tutor_model",
    "grammar_checker": "tutor_model_low_resource",
    "sentence_maker": "tutor_model",
    "sentence_checker": "tutor_model_low_resource",
}

# Tasks that pin the stronger model on a low-resource language (drafting/chat
# where the error cost is highest). Checkers already use the stronger model;
# summary/translate stay on the configured default regardless of language.
_LOW_RESOURCE_PINNED = frozenset(
    {"tutor_chat", "reader", "grammar_maker", "sentence_maker", "level_estimate"}
)


def resolve_model(
    task: str, language_code: str | None = None, override: str | None = None
) -> str:
    """The model for *task*.

    Priority: explicit override (e.g. an admin per-language setting) >
    low-resource pin (for drafting/chat tasks) > the task's configured model.
    An unknown task falls back to the tutor chat model so a caller never gets
    an empty string.

    *override* is a substitute for the `tutor_model` SETTING FIELD only — it
    is silently ignored for a task whose field is `tutor_model_low_resource`
    (a checker) or `tutor_summary_model` (summary/translate/semantic_check).
    Admins have exactly one per-language override column
    (`languages.tutor_model`), and passing it uniformly into every
    resolve_model() call — including checkers — would let a maker-tier
    override quietly weaken a checker below the "verify one tier up" floor
    (§6: never self-certify). Gating on the field, not the task name, means
    every caller can pass the same override in without needing to reason
    about which tasks are safe to override.
    """
    field = TASK_MODELS.get(task, "tutor_model")
    if override and field == "tutor_model":
        return override
    settings = get_settings()
    if language_code in LOW_RESOURCE_LANGUAGES and task in _LOW_RESOURCE_PINNED:
        return settings.tutor_model_low_resource
    return getattr(settings, field)
