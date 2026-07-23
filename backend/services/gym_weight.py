"""Adaptive Gym: turn a learner's per-drill history into a selection weight.

Pure and deterministic — the persisted `gym_progress` stats (plus whether the
form is irregular) go in, a positive weight comes out, and the Gym samples
drills in proportion (higher weight → shown sooner / more often). Keeping this a
pure function means the whole weighting policy is unit-testable and tunable
without a migration.

Factors, and how they move the weight:
  * unseen              -> high (novelty; you haven't practised it yet)
  * misses / wrong-form -> up  (a real FORM error counts more than a typo)
  * hint dependence     -> up  (right, but only after revealing OPTIONAL help —
                                the always-shown baseline prompt is the question,
                                not a hint, so it never feeds this signal)
  * time since last seen-> up  (forgetting curve; recent drills fade)
  * mastery streak      -> down (clean, no-hint corrects = learned)
  * irregular form      -> up   (worth extra reps)
  * irregular + still failing -> floored HIGH so it keeps coming back even as
                                 the repeat-penalty would otherwise bury it
"""

from __future__ import annotations

# Tunables (kept together so the policy is legible and adjustable).
_UNSEEN_WEIGHT = 3.0
_BASELINE = 0.4              # a seen-but-average drill's floor before factors
_STRUGGLE_GAIN = 2.0        # how hard misses/hints pull the weight up
_WRONG_FORM_BONUS = 1.0     # a form error is worth this much extra vs a plain miss
_HINT_WEIGHT = 0.5          # a hinted-correct is "half a miss" of shakiness
_SPACING_FULL_DAYS = 7.0    # age at which the spacing term saturates
_SPACING_FLOOR = 0.3        # even a just-seen drill keeps this fraction
_IRREGULAR_MULT = 1.5
_IRREGULAR_FAILING_FLOOR = 2.5
_MIN_WEIGHT = 0.05


def drill_weight(stats: dict | None, is_irregular: bool = False) -> float:
    """Selection weight for one drill given the learner's *stats* (from
    gym_progress, or None if never seen) and whether the form is irregular."""
    if not stats or stats.get("seen", 0) <= 0:
        weight = _UNSEEN_WEIGHT
    else:
        seen = stats["seen"]
        # Shakiness per exposure: form errors weigh more than plain misses,
        # and leaning on the hint is partial evidence of not knowing it.
        struggle = (
            stats["misses"]
            + _WRONG_FORM_BONUS * stats["wrong_form"]
            + _HINT_WEIGHT * stats["hint_used"]
        ) / seen
        # Clean, no-hint corrects in a row damp the weight toward mastery.
        mastery = 1.0 / (1.0 + stats["streak"])
        # Spacing: recently seen fades, week-old resurfaces.
        days = stats["age_seconds"] / 86400.0
        recency = _SPACING_FLOOR + (1.0 - _SPACING_FLOOR) * min(1.0, days / _SPACING_FULL_DAYS)
        weight = (_BASELINE + _STRUGGLE_GAIN * struggle) * mastery * recency

    if is_irregular:
        weight *= _IRREGULAR_MULT
        # Irregular AND still getting the form wrong: keep it coming back hard,
        # overriding the repeat/mastery damping (owner's "unless irregular and
        # you keep failing it — that is slightly different").
        if stats and stats.get("wrong_form", 0) > 0:
            weight = max(weight, _IRREGULAR_FAILING_FLOOR)

    return max(_MIN_WEIGHT, weight)
