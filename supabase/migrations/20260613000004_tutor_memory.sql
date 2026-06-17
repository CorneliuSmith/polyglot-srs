-- Migration: AI tutor learner memory
-- Two-tier durable memory so the tutor remembers a student across sessions:
--   tutor_user_profile     — global facts (native language, motivation, other
--                            languages) that cause cross-language interference
--                            and are independent of which language is studied.
--   tutor_language_profile — per-(user, language) state: proficiency, the
--                            qualitative error patterns the SRS can't capture,
--                            topics covered, and a rolling session summary.
-- The SRS tables already hold vocab/grammar mastery; this captures only what
-- they cannot. Written by the tutor's `remember` tool and the post-session
-- summarizer, both running under the user's own RLS context.

CREATE TABLE tutor_user_profile (
    user_id     UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    profile     JSONB       NOT NULL DEFAULT '{}',
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE tutor_user_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tutor_user_profile_select_own"
    ON tutor_user_profile FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "tutor_user_profile_insert_own"
    ON tutor_user_profile FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "tutor_user_profile_update_own"
    ON tutor_user_profile FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);


CREATE TABLE tutor_language_profile (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     UUID        NOT NULL REFERENCES languages(id),
    profile         JSONB       NOT NULL DEFAULT '{}',
    session_summary TEXT        NOT NULL DEFAULT '',
    last_session_at TIMESTAMPTZ,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, language_id)
);

CREATE INDEX idx_tutor_language_profile_user
    ON tutor_language_profile (user_id, language_id);

ALTER TABLE tutor_language_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "tutor_language_profile_select_own"
    ON tutor_language_profile FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "tutor_language_profile_insert_own"
    ON tutor_language_profile FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "tutor_language_profile_update_own"
    ON tutor_language_profile FOR UPDATE USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
