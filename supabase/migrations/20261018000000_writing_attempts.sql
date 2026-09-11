-- Write: the assessed-attempt log (docs/plans/handwriting.md, §6).
--
-- One row per Check: what the learner was asked to write, what the reader
-- read, whether it matched, how legible, how sure. NEVER the ink itself —
-- handwriting is as personal as a voice recording, and Speak keeps no
-- audio. The client draws the neatness panel from the strokes it holds;
-- the server only ever sees a PNG for the length of one model call.
--
-- Probed (repositories/write.py): a database without this table records
-- nothing and the assessment still returns, so the code can deploy ahead
-- of the push as usual.

CREATE TABLE IF NOT EXISTS writing_attempts (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    kind        TEXT        NOT NULL CHECK (kind IN ('sentence', 'word', 'free')),
    target      TEXT,                          -- what was asked; null for free writing
    read_as     TEXT        NOT NULL,          -- the transcription
    matches     BOOLEAN     NOT NULL,
    legibility  SMALLINT    NOT NULL CHECK (legibility BETWEEN 1 AND 5),
    confidence  TEXT        NOT NULL CHECK (confidence IN ('low', 'medium', 'high')),
    feedback    JSONB       NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS writing_attempts_user_idx
    ON writing_attempts (user_id, language_id, created_at DESC);

ALTER TABLE writing_attempts ENABLE ROW LEVEL SECURITY;

CREATE POLICY writing_attempts_select_own ON writing_attempts
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY writing_attempts_insert_own ON writing_attempts
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
