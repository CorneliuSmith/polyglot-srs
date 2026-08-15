-- Synthesize once, ever — even when the CDN upload fails.
--
-- tts_audio.storage_path was NOT NULL, so a clip could only be recorded if
-- its upload to the storage bucket succeeded. When the upload failed the
-- audio was served to the learner inline and then thrown away, and NOTHING
-- recorded that it had ever been made. Every later play of that sentence
-- paid Azure again, forever.
--
-- That is not a rare path. The uploader itself documents that the DO deploy
-- cannot reliably reach Supabase's HTTP APIs (the same egress quirk as the
-- account-creation admin API), which is why it has a timeout and a
-- ten-minute cooldown. Every clip whose first play landed inside one of
-- those windows is still being re-synthesized today.
--
-- Two changes make the cache durable:
--
--   * storage_path becomes nullable — a row can now mean "we have this
--     audio" without also meaning "it reached the CDN";
--   * audio holds the MP3 bytes for exactly those rows.
--
-- A DB-held clip is a fallback, not the destination: the router promotes it
-- to storage on the next play once uploads are working again, and clears
-- the bytes when it does. So the table holds only what the CDN has not
-- taken yet, and the app pays the synthesis provider once per distinct
-- (voice, text) no matter what the network did that day.

ALTER TABLE tts_audio ALTER COLUMN storage_path DROP NOT NULL;

ALTER TABLE tts_audio ADD COLUMN IF NOT EXISTS audio BYTEA;

-- A row has to be one or the other, or it is a cache entry pointing at
-- nothing — which would report a hit and then serve silence.
ALTER TABLE tts_audio DROP CONSTRAINT IF EXISTS tts_audio_has_clip;
ALTER TABLE tts_audio ADD CONSTRAINT tts_audio_has_clip
    CHECK (storage_path IS NOT NULL OR audio IS NOT NULL);

-- The promotion sweep's read: "which clips are still waiting for the CDN".
CREATE INDEX IF NOT EXISTS idx_tts_audio_pending_upload
    ON tts_audio (created_at) WHERE storage_path IS NULL;
