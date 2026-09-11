-- Write adapts to the learner's hand (docs/plans/handwriting.md, §11).
--
-- Three tables, all the learner's own:
--   writing_settings  — the account toggle "Adapt to my handwriting".
--                       Absent row = on. Off deletes everything below and
--                       stops collecting.
--   writing_profiles  — per (learner, language): the hand's known habits
--                       (letter, note, count, whether the writer confirmed
--                       the form legible) and running stats. What stops
--                       the reader repeating the same note.
--   writing_samples   — per (learner, language): a few of their OWN
--                       samples (PNG of the canvas, the text it reads, and
--                       the strokes it was made with — order, direction,
--                       lifts, speed: the METHOD, not only the shape),
--                       kept only with the toggle on, capped at twelve per
--                       language in code, shown to the reader as reference
--                       so it learns this hand. The ONLY place ink is ever
--                       stored, and the learner's to delete: Reset in
--                       Account, or the toggle.
--
-- Probed (repositories/write.py): a database without these behaves as
-- Phase 1 did — the reader sees no references and nothing is kept.

CREATE TABLE IF NOT EXISTS writing_settings (
    user_id     UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    adapt       BOOLEAN     NOT NULL DEFAULT true,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS writing_profiles (
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    habits      JSONB       NOT NULL DEFAULT '[]'::jsonb,
    stats       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, language_id)
);

CREATE TABLE IF NOT EXISTS writing_samples (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    text        TEXT        NOT NULL,
    image       BYTEA       NOT NULL,
    strokes     JSONB,                                 -- how it was made: [[[x,y,t],…],…]
    method      JSONB       NOT NULL DEFAULT '{}'::jsonb,  -- summarize_method() of the strokes
    confirmed   BOOLEAN     NOT NULL DEFAULT false,   -- by the writer, not the reader
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS writing_samples_user_idx
    ON writing_samples (user_id, language_id, confirmed DESC, created_at DESC);

ALTER TABLE writing_settings ENABLE ROW LEVEL SECURITY;
ALTER TABLE writing_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE writing_samples  ENABLE ROW LEVEL SECURITY;

CREATE POLICY writing_settings_own ON writing_settings
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY writing_profiles_own ON writing_profiles
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
CREATE POLICY writing_samples_own ON writing_samples
    FOR ALL TO authenticated USING (user_id = auth.uid()) WITH CHECK (user_id = auth.uid());
