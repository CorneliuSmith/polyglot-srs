-- Speak (docs/plans/speak.md) — conversation practice with a correction pass.
--
-- Stage 1 of the plan: a typed conversation partner plus an end-of-session
-- breakdown. Speech and the interrupting Coach correction come later; the
-- schema below already carries what they need (audio_ms, mode) so those
-- stages add behaviour, not columns.
--
-- Two tables, because a turn is written once and read once. The error list
-- rides the turn as JSONB rather than getting its own table: nothing queries
-- across sessions yet, and inventing an errors table now would fix a shape
-- before anything has asked a question of it.

CREATE TABLE IF NOT EXISTS speak_sessions (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        REFERENCES languages(id),
    -- 'flow' corrects only at the end; 'coach' corrects as you go (stage 3).
    -- Stored per session because it changes what the learner was shown, so
    -- reading an old session back has to know which it was.
    mode        TEXT        NOT NULL DEFAULT 'flow',
    -- Free text the learner chose, or NULL for "anything — you start".
    topic       TEXT,
    started_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- NULL while the session is live. A session abandoned mid-turn keeps
    -- ended_at NULL and its turns stay readable: the plan requires the
    -- summary be computable from whatever happened, so nothing here treats
    -- "unfinished" as "discard".
    ended_at    TIMESTAMPTZ,
    turn_count  INT         NOT NULL DEFAULT 0,
    -- The end-of-session breakdown, once computed. NULL until they finish.
    summary     JSONB
);

CREATE INDEX IF NOT EXISTS idx_speak_sessions_user_lang
    ON speak_sessions (user_id, language_id, started_at DESC);

CREATE TABLE IF NOT EXISTS speak_turns (
    session_id   UUID        NOT NULL
                             REFERENCES speak_sessions(id) ON DELETE CASCADE,
    idx          INT         NOT NULL,
    learner_text TEXT        NOT NULL,
    partner_text TEXT        NOT NULL,
    -- How long they spoke, once stage 2 lands audio. NULL for typed turns,
    -- which is every turn today.
    audio_ms     INT,
    -- [{type, learner_said, should_be, note}, …] — what the model noticed
    -- this turn. In flow mode the learner never sees these until the end.
    errors       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (session_id, idx)
);

ALTER TABLE speak_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE speak_turns    ENABLE ROW LEVEL SECURITY;

CREATE POLICY speak_sessions_select_own ON speak_sessions
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY speak_sessions_insert_own ON speak_sessions
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY speak_sessions_update_own ON speak_sessions
    FOR UPDATE TO authenticated USING (user_id = auth.uid())
                                WITH CHECK (user_id = auth.uid());

-- A turn has no user_id of its own; ownership is the parent session's. The
-- EXISTS runs against speak_sessions, which is itself RLS'd, so a turn is
-- reachable only through a session the caller can already see.
CREATE POLICY speak_turns_select_own ON speak_turns
    FOR SELECT TO authenticated USING (
        EXISTS (SELECT 1 FROM speak_sessions s
                 WHERE s.id = speak_turns.session_id AND s.user_id = auth.uid())
    );
CREATE POLICY speak_turns_insert_own ON speak_turns
    FOR INSERT TO authenticated WITH CHECK (
        EXISTS (SELECT 1 FROM speak_sessions s
                 WHERE s.id = speak_turns.session_id AND s.user_id = auth.uid())
    );
