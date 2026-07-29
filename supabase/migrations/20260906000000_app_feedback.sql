-- Migration: general app feedback
--
-- Every feedback channel that existed was scoped to a piece of CONTENT — a
-- card, a grammar point, a sentence. A beta user who wanted to say "the
-- keyboard is cut off on my phone" or "I can't find the Gym" had nowhere to
-- put it and no reason to believe anyone would see it if they did. This is
-- the general channel, reachable from the home page.
--
-- Same trust model as card_feedback: a user reads and writes only their own
-- rows under RLS; staff read all of them through a privileged connection
-- after the app-layer role check.

CREATE TABLE IF NOT EXISTS app_feedback (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    -- Nullable: feedback about the app as a whole belongs to no language, and
    -- forcing a choice would make people pick one at random.
    language_id  UUID        REFERENCES languages(id) ON DELETE SET NULL,
    category     TEXT        NOT NULL CHECK (category IN (
                                 'bug', 'confusing', 'content', 'idea', 'other')),
    message      TEXT        NOT NULL CHECK (length(btrim(message)) > 0),
    -- Where they were when they hit Send. Filled in by the client, not typed:
    -- "which page was this?" is the first question anyone triaging asks, and
    -- the reporter should not have to answer it.
    page         TEXT,
    status       TEXT        NOT NULL DEFAULT 'open'
                             CHECK (status IN ('open', 'triaged', 'closed')),
    -- Staff reply/disposition, so triage is not kept in someone's head.
    admin_note   TEXT,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The triage view: open items first, newest first, optionally per language.
CREATE INDEX IF NOT EXISTS idx_app_feedback_status_created
    ON app_feedback (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_app_feedback_language
    ON app_feedback (language_id, created_at DESC);

ALTER TABLE app_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "app_feedback_insert_own"
    ON app_feedback FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "app_feedback_select_own"
    ON app_feedback FOR SELECT USING (auth.uid() = user_id);
