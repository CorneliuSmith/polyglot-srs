-- Adaptive Gym: per-learner, per-drill practice history (WP).
--
-- The Gym was ungraded and recorded nothing, so it couldn't adapt — it showed
-- the same handful of drills on a fixed daily rotation. This table persists a
-- learner's history with each drill so selection can weight what to show next:
-- forms they miss (especially real wrong-FORM errors, not typos), forms they
-- lean on hints for, and forms they haven't seen in a while come back; forms
-- they've cleanly mastered and just-seen drills fade. Misses on IRREGULAR forms
-- keep coming back even when otherwise down-weighted.
--
-- Stats are the durable truth; the selection weight is computed from them at
-- pick time, so the weighting can be tuned without a migration. Ungraded still:
-- nothing here touches the SRS schedule (user_cards / review_log).

CREATE TABLE gym_progress (
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    drill_id     UUID        NOT NULL REFERENCES drill_sentences(id) ON DELETE CASCADE,
    seen         INT         NOT NULL DEFAULT 0,   -- times shown in the Gym
    misses       INT         NOT NULL DEFAULT 0,   -- any non-correct result
    wrong_form   INT         NOT NULL DEFAULT 0,   -- the target skill: a real form error
    hint_used    INT         NOT NULL DEFAULT 0,   -- correct-but-hinted counts as shaky
    streak       INT         NOT NULL DEFAULT 0,   -- consecutive clean (no-hint) corrects
    last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, drill_id)
);

CREATE INDEX idx_gym_progress_user ON gym_progress (user_id);

-- RLS: a learner sees and writes only their own rows (same policy shape as
-- review_log / user_cards).
ALTER TABLE gym_progress ENABLE ROW LEVEL SECURITY;

CREATE POLICY "gym_progress_select_own"
    ON gym_progress FOR SELECT
    USING (user_id = auth.uid());

CREATE POLICY "gym_progress_insert_own"
    ON gym_progress FOR INSERT
    WITH CHECK (user_id = auth.uid());

CREATE POLICY "gym_progress_update_own"
    ON gym_progress FOR UPDATE
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
