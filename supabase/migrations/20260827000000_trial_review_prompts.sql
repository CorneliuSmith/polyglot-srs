-- Trial reviewers get "nudged" into actually reviewing: occasionally, when they
-- open the dashboard, a blocking prompt asks them to judge one real pending item
-- (a generated drill or example) before they proceed. Their answer is recorded
-- as an advisory recommendation — the same signal the Review queue already uses.
--
-- This table is just the cadence bookkeeping: when a trial reviewer last
-- answered a prompt, so we can rate-limit the nudge to roughly once a day.

CREATE TABLE IF NOT EXISTS trial_review_prompt_state (
    user_id          UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    last_answered_at TIMESTAMPTZ,
    prompts_answered INT NOT NULL DEFAULT 0
);

-- Privileged access only (the app decides eligibility + cadence); RLS on with
-- no authenticated policy, same pattern as the other contributor-domain tables.
ALTER TABLE trial_review_prompt_state ENABLE ROW LEVEL SECURITY;
