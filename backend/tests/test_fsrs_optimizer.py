"""Tests for the FSRS weight optimizer (pure, synthetic data)."""
from __future__ import annotations

import random

from backend.services.fsrs import (
    DEFAULT_PARAMS,
    Rating,
    next_state,
    retrievability,
)
from backend.services.fsrs_optimizer import (
    PARAM_BOUNDS,
    fit_weights,
    log_loss,
)


def _simulate(true_w, n_cards, n_reviews, rng):
    """Generate review sequences whose recall really follows *true_w*."""
    sequences = []
    for _ in range(n_cards):
        seq = [(0.0, int(Rating.GOOD))]
        stability, difficulty = next_state(true_w, None, None, Rating.GOOD, 0.0)
        for _ in range(n_reviews - 1):
            elapsed = rng.uniform(0.5, max(1.0, stability))
            r = retrievability(elapsed, stability)
            grade = Rating.GOOD if rng.random() < r else Rating.AGAIN
            seq.append((elapsed, int(grade)))
            stability, difficulty = next_state(true_w, stability, difficulty, grade, elapsed)
        sequences.append(seq)
    return sequences


# A "true" model that forgets much faster than the defaults: tiny initial
# stabilities. Data drawn from it should be poorly explained by the defaults.
_FAST_FORGET = (
    0.1, 0.3, 0.6, 2.0, *DEFAULT_PARAMS[4:]
)


class TestLogLoss:
    def test_nonnegative(self):
        rng = random.Random(1)
        seqs = _simulate(DEFAULT_PARAMS, 10, 8, rng)
        assert log_loss(DEFAULT_PARAMS, seqs) >= 0.0

    def test_zero_when_nothing_scorable(self):
        # sequences of length 1 have no prior to predict from
        assert log_loss(DEFAULT_PARAMS, [[(0.0, 3)], [(0.0, 2)]]) == 0.0


class TestFit:
    def test_returns_none_when_no_scorable_reviews(self):
        assert fit_weights([[(0.0, 3)]]) is None
        assert fit_weights([]) is None

    def test_fit_never_worse_than_starting_point(self):
        rng = random.Random(7)
        seqs = _simulate(_FAST_FORGET, 40, 10, rng)
        baseline = log_loss(DEFAULT_PARAMS, seqs)
        result = fit_weights(seqs)
        assert result is not None
        # L-BFGS-B starts at the defaults, so it can only match or improve.
        assert result.log_loss <= baseline + 1e-9

    def test_fit_improves_on_mismatched_data(self):
        rng = random.Random(11)
        seqs = _simulate(_FAST_FORGET, 60, 12, rng)
        baseline = log_loss(DEFAULT_PARAMS, seqs)
        result = fit_weights(seqs)
        assert result is not None
        # The defaults badly misjudge a fast-forgetting population; the fit
        # should be a real improvement, not a rounding-level one.
        assert result.log_loss < baseline - 1e-3

    def test_fitted_params_are_valid(self):
        rng = random.Random(3)
        seqs = _simulate(_FAST_FORGET, 30, 10, rng)
        result = fit_weights(seqs)
        assert result is not None
        assert len(result.params) == 19
        for value, (lo, hi) in zip(result.params, PARAM_BOUNDS):
            assert lo - 1e-9 <= value <= hi + 1e-9
        assert result.n_reviews == 30 * 9  # (n_reviews - 1) per card

    def test_deterministic(self):
        rng = random.Random(5)
        seqs = _simulate(_FAST_FORGET, 25, 9, rng)
        a = fit_weights(seqs)
        b = fit_weights(seqs)
        assert a is not None and b is not None
        assert a.params == b.params
