-- Contributor-recorded audio (owner: "On Jamaican patois, give the
-- disclaimer that we are working on finding recordings - and build in some
-- contributor functionality to provide recordings").
--
-- Jamaican Patois has no neural TTS voice on any provider — deliberately
-- absent from the VOICES map — so its audio has to come from people. A
-- contributor records a clip for one exact text (a word, a drill sentence,
-- an example); a reviewer approves it; the audio endpoint then serves the
-- approved clip exactly where synthesized TTS would have been, for ANY
-- language (a human recording outranks a synthetic voice when both exist).
--
-- Bytes live in the row (BYTEA), not the storage bucket: clips are short,
-- the review queue needs them before they're public, and the DO deploy's
-- storage-egress quirk (see routers/audio.py) makes bucket uploads
-- best-effort anyway. One (language, contributor, text) row — resubmitting
-- replaces your own take and sends it back to review.

CREATE TABLE IF NOT EXISTS contributor_recordings (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id    UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    contributor_id UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    text           TEXT        NOT NULL CHECK (char_length(text) <= 300),
    audio          BYTEA       NOT NULL,
    mime           TEXT        NOT NULL DEFAULT 'audio/webm'
                                CHECK (mime IN ('audio/webm', 'audio/ogg',
                                                'audio/mpeg', 'audio/mp4',
                                                'audio/wav')),
    status         TEXT        NOT NULL DEFAULT 'pending'
                                CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewed_by    UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (language_id, contributor_id, text)
);

-- The audio endpoint's lookup: newest approved clip for (language, text).
CREATE INDEX IF NOT EXISTS idx_contributor_recordings_lookup
    ON contributor_recordings (language_id, text)
    WHERE status = 'approved';

-- The review queue: pending clips per language, oldest first.
CREATE INDEX IF NOT EXISTS idx_contributor_recordings_queue
    ON contributor_recordings (language_id, status, created_at);

ALTER TABLE contributor_recordings ENABLE ROW LEVEL SECURITY;

-- Contributors see their own submissions; everything else (the review
-- queue, approval writes, learner-facing serving) goes through the API on
-- the service role. RLS on with only this policy = no other direct access.
CREATE POLICY contributor_recordings_select_own ON contributor_recordings
    FOR SELECT USING (auth.uid() = contributor_id);
