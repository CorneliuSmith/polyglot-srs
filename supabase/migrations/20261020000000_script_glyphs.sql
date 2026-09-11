-- The stroke library (docs/plans/handwriting.md, §5–6): how each letter
-- is written, authored by a speaker in the Workshop's Strokes panel, and
-- the exemplar sentences written in one flow that are the Learn models
-- and the composer's yardstick.
--
--   script_glyphs     — one row per (script, glyph, form, style): the
--                       ordered strokes in a 1000×1000 box ([[x,y],…] per
--                       stroke), the entry/exit points for joining scripts,
--                       a hint per stroke, and a reviewed flag. Unreviewed
--                       rows are drafts: the Workshop shows them, the
--                       learner's guided Letters never do.
--   script_exemplars  — one row per sentence a speaker wrote whole.
--
-- Content is shared and readable by any signed-in user; writes go through
-- the contributor endpoints on a privileged connection, gated by the
-- language roles. Probed by every reader.

CREATE TABLE IF NOT EXISTS script_glyphs (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    script      TEXT        NOT NULL,
    glyph       TEXT        NOT NULL,
    form        TEXT        NOT NULL,
    style       TEXT        NOT NULL DEFAULT 'print',
    strokes     JSONB       NOT NULL,
    joins       JSONB       NOT NULL DEFAULT '{}'::jsonb,
    hints       JSONB       NOT NULL DEFAULT '[]'::jsonb,
    source      TEXT        NOT NULL DEFAULT 'workshop',
    reviewed    BOOLEAN     NOT NULL DEFAULT false,
    created_by  UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (script, glyph, form, style)
);

CREATE TABLE IF NOT EXISTS script_exemplars (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    script        TEXT        NOT NULL,
    language_code TEXT        NOT NULL,
    style         TEXT        NOT NULL DEFAULT 'print',
    text          TEXT        NOT NULL,
    strokes       JSONB       NOT NULL,
    source        TEXT        NOT NULL DEFAULT 'workshop',
    reviewed      BOOLEAN     NOT NULL DEFAULT false,
    created_by    UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS script_glyphs_script_idx ON script_glyphs (script, style, reviewed);
CREATE INDEX IF NOT EXISTS script_exemplars_script_idx ON script_exemplars (script, style, reviewed);

ALTER TABLE script_glyphs    ENABLE ROW LEVEL SECURITY;
ALTER TABLE script_exemplars ENABLE ROW LEVEL SECURITY;

CREATE POLICY script_glyphs_read ON script_glyphs
    FOR SELECT TO authenticated USING (true);
CREATE POLICY script_exemplars_read ON script_exemplars
    FOR SELECT TO authenticated USING (true);
