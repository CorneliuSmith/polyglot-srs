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


@dataclass
class ValidatedFit:
    """A fit judged on data it never saw (WP8 quality gate).

    `adopted` is the verdict: the (shrunk) fitted params beat the defaults on
    the held-out tail of each card's history. Store-and-use only when True.
    """
    params: list[float]
    train_log_loss: float
    holdout_log_loss: float
    defaults_holdout_log_loss: float
    n_reviews: int          # scorable reviews in the training split
    n_holdout_reviews: int  # scorable reviews in the held-out tails
    adopted: bool


def _scorable_reviews(sequences: list[ReviewSequence]) -> int:
    return sum(max(len(s) - 1, 0) for s in sequences)


def log_loss(
    params: tuple[float, ...],
    sequences: list[ReviewSequence],
    score_from: list[int] | None = None,
) -> float:
    """Mean binary cross-entropy of predicted recall over scorable reviews.

    *score_from*, when given, holds one index per sequence: the memory state
    is simulated from the start, but only reviews at that index or later
    contribute to the loss — this is how the held-out tail of a card's
    history is scored without leaking it into the fit.
    """
    total = 0.0
    n = 0
    for si, seq in enumerate(sequences):
        start = score_from[si] if score_from is not None else 1
        stability: float | None = None
        difficulty: float | None = None
        for i, (elapsed, grade) in enumerate(seq):
            if i >= max(start, 1):
                r = retrievability(max(0.0, elapsed), stability)
                recalled = 0.0 if grade == Rating.AGAIN else 1.0
                p = min(max(r, _EPS), 1.0 - _EPS)
                total += -(recalled * math.log(p) + (1.0 - recalled) * math.log(1.0 - p))
                n += 1
            stability, difficulty = next_state(params, stability, difficulty, grade, elapsed)
    return total / n if n else 0.0


def split_holdout(
    sequences: list[ReviewSequence], fraction: float = 0.2
) -> tuple[list[ReviewSequence], list[int]]:
    """Split each card's history in time: first (1-fraction) train, rest held out.

    Returns (train_sequences, holdout_start_indices). The start index refers
    to the FULL sequence — cards too short to donate a tail get a start index
    past their end and contribute nothing to the held-out loss.
    """
    train: list[ReviewSequence] = []
    starts: list[int] = []
    for seq in sequences:
        split_idx = max(1, math.floor(len(seq) * (1.0 - fraction)))
        train.append(seq[:split_idx])
        starts.append(split_idx)
    return train, starts


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


# Shrinkage constant: with n training reviews, the fit moves
# n / (n + SHRINK_K) of the way from the defaults toward the raw fit —
# small datasets stay close to the defaults, big ones trust the data.
SHRINK_K = 300


def fit_weights_validated(
    sequences: list[ReviewSequence],
    *,
    x0: tuple[float, ...] = DEFAULT_PARAMS,
    holdout_fraction: float = 0.2,
    shrink_k: int = SHRINK_K,
    max_sequences: int = MAX_SEQUENCES,
    seed: int = 0,
) -> ValidatedFit | None:
    """Fit on the first 80% of each card's history, judge on the last 20%.

    The candidate (fitted params shrunk toward the defaults by data volume)
    is adopted only when its held-out log-loss strictly beats the defaults'
    held-out log-loss — a fit that merely memorized its training data never
    replaces the defaults. Returns None when there's nothing to fit or
    nothing to validate on.
    """
    if len(sequences) > max_sequences:
        sequences = random.Random(seed).sample(sequences, max_sequences)

    train, starts = split_holdout(sequences, holdout_fraction)
    n_holdout = sum(
        max(len(seq) - max(start, 1), 0) for seq, start in zip(sequences, starts)
    )
    if n_holdout == 0:
        return None

    fit = fit_weights(train, x0=x0, max_sequences=max_sequences, seed=seed)
    if fit is None:
        return None

    shrink = fit.n_reviews / (fit.n_reviews + shrink_k)
    candidate = [
        max(lo, min(hi, d + (f - d) * shrink))
        for f, d, (lo, hi) in zip(fit.params, x0, PARAM_BOUNDS)
    ]

    holdout_loss = log_loss(tuple(candidate), sequences, score_from=starts)
    defaults_loss = log_loss(tuple(x0), sequences, score_from=starts)

    return ValidatedFit(
        params=candidate,
        train_log_loss=fit.log_loss,
        holdout_log_loss=holdout_loss,
        defaults_holdout_log_loss=defaults_loss,
        n_reviews=fit.n_reviews,
        n_holdout_reviews=n_holdout,
        adopted=holdout_loss < defaults_loss,
    )
