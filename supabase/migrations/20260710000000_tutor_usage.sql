-- Tutor usage log: one row per answered tutor message.
--
-- This is the unit LEARNERS see (messages), never the unit they're billed
-- by — pricing is flat per tier; allowances are fair-use cost protection:
--   free account:  N messages / month  (taste the tutor, SRS is never gated)
--   plus account:  N messages / day    (flat subscription price, daily reset)
-- Token columns are for the OPERATOR's cost monitoring (WP9b), nullable
-- until capture is wired.

CREATE TABLE IF NOT EXISTS tutor_usage (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id   UUID        REFERENCES languages(id),
    model         TEXT,
    input_tokens  INTEGER,
    output_tokens INTEGER,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tutor_usage_user_time
    ON tutor_usage (user_id, created_at);

ALTER TABLE tutor_usage ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tutor_usage_select_own"
    ON tutor_usage FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "tutor_usage_insert_own"
    ON tutor_usage FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);
