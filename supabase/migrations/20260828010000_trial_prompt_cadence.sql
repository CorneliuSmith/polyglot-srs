-- Adaptive cadence for the trial-reviewer nudge: the more real feedback a
-- reviewer gives, the further out the next check-in is scheduled; a skip brings
-- it back sooner, so skipping isn't a way to dodge. We store the computed
-- next_prompt_at (rather than deriving it each read) and count skips separately.

ALTER TABLE trial_review_prompt_state
    ADD COLUMN IF NOT EXISTS prompts_skipped INT NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS next_prompt_at  TIMESTAMPTZ;
