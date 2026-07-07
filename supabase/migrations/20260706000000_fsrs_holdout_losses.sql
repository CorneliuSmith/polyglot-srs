-- WP8: FSRS held-out quality gate.
--
-- Fitted weights are only adopted when they beat the built-in defaults on the
-- last 20% of each card's review history (data the fit never saw). Store both
-- held-out losses so every adopted fit carries the evidence it won on.

ALTER TABLE fsrs_weights
    ADD COLUMN IF NOT EXISTS holdout_log_loss          DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS defaults_holdout_log_loss DOUBLE PRECISION;
