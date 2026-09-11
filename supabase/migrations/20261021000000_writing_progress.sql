-- Guided Letters (docs/plans/handwriting.md, Phase 3): what a learner has
-- written well, per letter form, so the strip at the top of Write fills
-- in and weak letters can be revisited. One row per (learner, glyph form);
-- the row is the learner's, like every progress row. Probed by its reader.

CREATE TABLE IF NOT EXISTS writing_progress (
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    glyph_id    UUID        NOT NULL REFERENCES script_glyphs(id) ON DELETE CASCADE,
    attempts    INTEGER     NOT NULL DEFAULT 0,
    passes      INTEGER     NOT NULL DEFAULT 0,
    best_score  REAL        NOT NULL DEFAULT 0,
    last_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, glyph_id)
);

ALTER TABLE writing_progress ENABLE ROW LEVEL SECURITY;
CREATE POLICY writing_progress_own ON writing_progress
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
