"""Fit FSRS-5 weights from review history.

The 19 FSRS parameters are fit by minimizing the prediction error of the
forgetting model: for every review that has a prior (so a retrievability can be
predicted), compare the model's predicted recall probability against what
actually happened (recalled = the grade wasn't *Again*), and minimize the binary
cross-entropy over the parameters with a bounded L-BFGS-B search.

Pure and dependency-light (numpy + scipy). The forward simulation reuses
`fsrs.next_state`, so the fitted model is exactly the one the scheduler runs.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass

import numpy as np
from scipy.optimize import minimize

from backend.services.fsrs import (
    DEFAULT_PARAMS,
    Rating,
    next_state,
    retrievability,
)

# A review sequence for one card: (elapsed_days_since_prev, grade) in time order.
# The first entry's elapsed is ignored (no prior memory state to predict from).
ReviewSequence = list[tuple[float, int]]

_EPS = 1e-6

# Per-parameter bounds for the FSRS-5 weights (the reference optimizer's clamps).
PARAM_BOUNDS: tuple[tuple[float, float], ...] = (
    (0.001, 100.0),   # w0  initial stability: Again
    (0.001, 100.0),   # w1  initial stability: Hard
    (0.001, 100.0),   # w2  initial stability: Good
    (0.001, 100.0),   # w3  initial stability: Easy
    (1.0, 10.0),      # w4  initial difficulty
    (0.001, 4.0),     # w5  initial difficulty
    (0.001, 4.0),     # w6  difficulty delta
    (0.0, 0.75),      # w7  difficulty mean reversion
    (0.0, 4.5),       # w8  stability (recall)
    (0.0, 0.8),       # w9
    (0.001, 3.5),     # w10
    (0.001, 5.0),     # w11 stability (forget)
    (0.001, 0.25),    # w12
    (0.001, 0.9),     # w13
    (0.0, 4.0),       # w14
    (0.0, 1.0),       # w15 hard penalty
    (1.0, 6.0),       # w16 easy bonus
    (0.0, 2.0),       # w17 short-term (unused in day scheduler, still fit)
    (0.0, 2.0),       # w18
)

# Cap the work per fit; sample cards beyond this so a popular language stays fast.
MAX_SEQUENCES = 5000


@dataclass
class FitResult:
    params: list[float]
    log_loss: float
    n_reviews: int  # number of scorable reviews (those with a prior)


def _scorable_reviews(sequences: list[ReviewSequence]) -> int:
    return sum(max(len(s) - 1, 0) for s in sequences)


def log_loss(params: tuple[float, ...], sequences: list[ReviewSequence]) -> float:
    """Mean binary cross-entropy of predicted recall over all scorable reviews."""
    total = 0.0
    n = 0
    for seq in sequences:
        stability: float | None = None
        difficulty: float | None = None
        for i, (elapsed, grade) in enumerate(seq):
            if i > 0:
                r = retrievability(max(0.0, elapsed), stability)
                recalled = 0.0 if grade == Rating.AGAIN else 1.0
                p = min(max(r, _EPS), 1.0 - _EPS)
                total += -(recalled * math.log(p) + (1.0 - recalled) * math.log(1.0 - p))
                n += 1
            stability, difficulty = next_state(params, stability, difficulty, grade, elapsed)
    return total / n if n else 0.0


def fit_weights(
    sequences: list[ReviewSequence],
    *,
    x0: tuple[float, ...] = DEFAULT_PARAMS,
    max_sequences: int = MAX_SEQUENCES,
    seed: int = 0,
) -> FitResult | None:
    """Fit FSRS weights to the given review sequences.

    Returns None when there's nothing to fit (no review has a prior state).
    Otherwise returns the best-fit params, the achieved mean log-loss, and how
    many reviews informed the fit.
    """
    if len(sequences) > max_sequences:
        sequences = random.Random(seed).sample(sequences, max_sequences)

    n_reviews = _scorable_reviews(sequences)
    if n_reviews == 0:
        return None

    result = minimize(
        lambda w: log_loss(tuple(w), sequences),
        x0=np.asarray(x0, dtype=float),
        method="L-BFGS-B",
        bounds=PARAM_BOUNDS,
        options={"maxiter": 200, "ftol": 1e-6},
    )
    params = [float(x) for x in result.x]
    return FitResult(params=params, log_loss=float(result.fun), n_reviews=n_reviews)
