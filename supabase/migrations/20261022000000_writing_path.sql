-- The learning path (docs/plans/handwriting.md, §13): which lessons of a
-- script's course a learner has finished, per style. Letter lessons
-- finish themselves from writing_progress; word and sentence lessons,
-- and lessons whose forms nobody has authored yet, are marked here.
-- Probed by its reader; the row is the learner's.

CREATE TABLE IF NOT EXISTS writing_path (
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    style       TEXT        NOT NULL,
    lesson_id   TEXT        NOT NULL,
    done_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, language_id, style, lesson_id)
);

ALTER TABLE writing_path ENABLE ROW LEVEL SECURITY;
CREATE POLICY writing_path_own ON writing_path
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
