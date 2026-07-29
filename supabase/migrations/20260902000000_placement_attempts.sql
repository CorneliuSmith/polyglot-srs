-- Placement attempts, per learner per language (owner, 2026-07-28).
--
-- Placement used to be a one-shot step inside signup: nothing recorded that
-- it happened, so the app could not tell a learner opening their FIRST
-- language from one returning to a language they'd already placed in, and
-- had no way to offer a retake or measure progress between attempts.
--
-- One row per attempt (not per learner) on purpose: keeping the history is
-- what lets a retake be compared against the previous estimate — "you were
-- A2 in March, you're B1 now" — and the row count is what varies the item
-- selection so a retake isn't the same questions over again.
CREATE TABLE IF NOT EXISTS placement_attempts (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    estimated_level TEXT,
    items_asked     INT         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- "Has this learner placed in this language, and how many times?" — the
-- question asked on every dashboard load for the active language.
CREATE INDEX IF NOT EXISTS idx_placement_attempts_user_language
    ON placement_attempts (user_id, language_id, created_at DESC);

ALTER TABLE placement_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY "placement_attempts_select_own"
    ON placement_attempts FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "placement_attempts_insert_own"
    ON placement_attempts FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "placement_attempts_delete_own"
    ON placement_attempts FOR DELETE USING (auth.uid() = user_id);
