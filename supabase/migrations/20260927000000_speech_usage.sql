-- Speech spend, recorded where it is actually incurred.
--
-- Neural TTS and speech-to-text are billed by the character and by the
-- audio second, not by the token, so tutor_usage cannot hold them and the
-- admin cost view had a blind spot exactly where the newest feature
-- spends money. Speak synthesizes every partner line inline and caches
-- none of it (each line is unique, and caching one side of somebody's
-- conversation is not something to store), so nothing on disk recorded
-- that spend either.
--
-- One row per BILLABLE event: a synthesis that actually reached the
-- provider (a cache hit costs nothing and writes nothing) and a
-- transcription. The audio itself is never stored — see the /transcribe
-- docstring; this table holds a duration and a language, never speech.
--
-- Service-role writes only, like tts_audio: RLS on, no policies. The
-- admin cost view reads it on a privileged connection.

CREATE TABLE IF NOT EXISTS speech_usage (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id       UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    language_code TEXT,
    -- 'tts' (characters synthesized) or 'stt' (audio transcribed).
    kind          TEXT        NOT NULL CHECK (kind IN ('tts', 'stt')),
    -- Which surface spent it: 'speak' (a conversation) or 'content' (the
    -- app reading its own teaching material out loud).
    feature       TEXT        NOT NULL,
    chars         INT         NOT NULL DEFAULT 0,
    audio_ms      INT         NOT NULL DEFAULT 0,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_speech_usage_created
    ON speech_usage (created_at DESC);

ALTER TABLE speech_usage ENABLE ROW LEVEL SECURITY;
