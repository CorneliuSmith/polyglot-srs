-- FSRS-5 scheduling.
--
-- Replaces SM-2's single ease factor with the two latent variables FSRS models:
--   stability  — days until recall probability decays to the target retention
--   difficulty — 1 (easy) .. 10 (hard)
-- plus the card's learning state. The legacy SM-2 columns (ease_factor,
-- interval, repetitions, streak, lapses) are kept so existing rows and any
-- analytics keep working; FSRS initializes stability/difficulty on a card's
-- next review.

ALTER TABLE user_cards
    ADD COLUMN IF NOT EXISTS stability  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS difficulty DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS state      TEXT NOT NULL DEFAULT 'new';

ALTER TABLE user_cards
    DROP CONSTRAINT IF EXISTS user_cards_state_check;
ALTER TABLE user_cards
    ADD CONSTRAINT user_cards_state_check
        CHECK (state IN ('new', 'learning', 'review', 'relearning'));

-- review_log: record the FSRS variables per review. FSRS has no ease factor,
-- so the legacy ease columns become optional.
ALTER TABLE review_log
    ALTER COLUMN ease_factor_before DROP NOT NULL,
    ALTER COLUMN ease_factor_after  DROP NOT NULL;

ALTER TABLE review_log
    ADD COLUMN IF NOT EXISTS stability_before  DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS stability_after   DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS difficulty_before DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS difficulty_after  DOUBLE PRECISION;

-- Supports the tutor's "weakest cards" ranking by difficulty.
CREATE INDEX IF NOT EXISTS idx_user_cards_user_language_difficulty
    ON user_cards (user_id, language_id, difficulty DESC);
