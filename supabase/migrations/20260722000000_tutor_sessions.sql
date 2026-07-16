-- WP18(a): append-only tutor session log (≈ the owner's claude_practice.md).
--
-- The rolling summary on user_language_profiles stays the "current state";
-- this table keeps one immutable row per ENDED session so continuity stops
-- washing out — the summarizer reads the last few rows for context, and the
-- tutor UI shows a "Past sessions" history.

CREATE TABLE IF NOT EXISTS tutor_sessions (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id    UUID        REFERENCES languages(id),
    summary        TEXT        NOT NULL,
    message_count  INT         NOT NULL DEFAULT 0,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_tutor_sessions_user_lang
    ON tutor_sessions (user_id, language_id, created_at DESC);

ALTER TABLE tutor_sessions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tutor_sessions_select_own ON tutor_sessions
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY tutor_sessions_insert_own ON tutor_sessions
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
