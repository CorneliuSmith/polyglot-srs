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
    fit_weights_validated,
    log_loss,
    split_holdout,
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


class TestSplitHoldout:
    def test_holds_out_the_last_fifth(self):
        seqs = [[(0.0, 3)] * 10]
        train, starts = split_holdout(seqs, 0.2)
        assert len(train[0]) == 8
        assert starts == [8]

    def test_short_sequences_keep_at_least_one_training_review(self):
        seqs = [[(0.0, 3)], [(0.0, 3), (1.0, 3)]]
        train, starts = split_holdout(seqs, 0.2)
        assert len(train[0]) == 1 and starts[0] == 1  # nothing to hold out
        assert len(train[1]) == 1 and starts[1] == 1  # last review held out

    def test_score_from_scores_only_the_tail(self):
        # A sequence whose tail is all failures: scoring only the tail must
        # differ from scoring the whole sequence.
        seq = [(0.0, 3), (1.0, 3), (1.0, 3), (1.0, 1), (1.0, 1)]
        full = log_loss(DEFAULT_PARAMS, [seq])
        tail = log_loss(DEFAULT_PARAMS, [seq], score_from=[3])
        assert tail != full
        assert tail > 0


class TestValidatedFit:
    def test_adopts_when_the_fit_beats_defaults_out_of_sample(self):
        # Data truly drawn from a fast-forgetting learner, reviewed at
        # multi-day gaps where the defaults are systematically overconfident
        # (they predict recall, the learner mostly forgets). The fitted
        # params must win on the held-out tails and be adopted.
        rng = random.Random(7)
        seqs = []
        for _ in range(80):
            seq = [(0.0, int(Rating.GOOD))]
            stability, difficulty = next_state(
                _FAST_FORGET, None, None, Rating.GOOD, 0.0
            )
            for _ in range(9):
                elapsed = rng.uniform(2.0, 10.0)
                r = retrievability(elapsed, stability)
                grade = Rating.GOOD if rng.random() < r else Rating.AGAIN
                seq.append((elapsed, int(grade)))
                stability, difficulty = next_state(
                    _FAST_FORGET, stability, difficulty, grade, elapsed
                )
            seqs.append(seq)
        result = fit_weights_validated(seqs, seed=7)
        assert result is not None
        assert result.n_holdout_reviews > 0
        assert result.holdout_log_loss < result.defaults_holdout_log_loss
        assert result.adopted
        for value, (lo, hi) in zip(result.params, PARAM_BOUNDS):
            assert lo <= value <= hi

    def test_rejects_a_fit_that_only_memorized_its_training_data(self):
        # Train prefix says "always forgotten", held-out tail says "always
        # recalled after long gaps": whatever the optimizer learns from the
        # prefix must do WORSE than the defaults on the tail -> rejected.
        seq = [(0.0, 3)] + [(1.0, 1)] * 7 + [(20.0, 3)] * 2
        seqs = [list(seq) for _ in range(40)]
        result = fit_weights_validated(seqs)
        assert result is not None
        assert result.holdout_log_loss >= result.defaults_holdout_log_loss
        assert not result.adopted

    def test_returns_none_without_a_holdout(self):
        # Single-review cards leave nothing to validate on.
        seqs = [[(0.0, 3)] for _ in range(10)]
        assert fit_weights_validated(seqs) is None

    def test_shrinks_toward_defaults_on_small_data(self):
        # A tiny dataset must produce params close to the defaults even if
        # the raw fit would wander: shrinkage is n / (n + K).
        rng = random.Random(3)
        seqs = _simulate(_FAST_FORGET, n_cards=4, n_reviews=6, rng=rng)
        result = fit_weights_validated(seqs, seed=3)
        assert result is not None
        # ~16 training reviews vs K=300 -> at most ~5% of the way to the fit.
        for value, default, (lo, hi) in zip(
            result.params, DEFAULT_PARAMS, PARAM_BOUNDS
        ):
            span = hi - lo
            assert abs(value - default) <= 0.1 * span + 1e-9
