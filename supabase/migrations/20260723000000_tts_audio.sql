-- WP7(a): cached neural TTS. One row per synthesized clip; the mp3 lives
-- in the public 'tts' storage bucket (audio of our own teaching content —
-- nothing sensitive). Generated on demand by the API on first play,
-- served from the CDN afterwards. Service-role writes only (RLS on, no
-- policies — user reads go straight to the public bucket URL).

CREATE TABLE IF NOT EXISTS tts_audio (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_code TEXT        NOT NULL,
    voice         TEXT        NOT NULL,
    text_hash     TEXT        NOT NULL,
    storage_path  TEXT        NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (voice, text_hash)
);

ALTER TABLE tts_audio ENABLE ROW LEVEL SECURITY;
