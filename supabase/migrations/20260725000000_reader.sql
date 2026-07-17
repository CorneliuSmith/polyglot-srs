-- WP21: The Reader — comprehensible input on demand.
--
-- readings: one generated text per row, stored with its full token-level
-- gloss map so the three-stage disclosure (guess → hover → explain) never
-- needs a second model call. Re-readable forever from the learner's shelf.
--
-- grammar_gap_log: when a generated text uses a structure the language's
-- grammar path doesn't cover, the gap is recorded here — the app collects
-- its own curriculum TODOs from real usage (owner request, 2026-07-16).

CREATE TABLE IF NOT EXISTS readings (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id  UUID        NOT NULL REFERENCES languages(id),
    topic        TEXT        NOT NULL,
    title        TEXT        NOT NULL,
    level        TEXT,                     -- CEFR the text was pitched at
    content      JSONB       NOT NULL,     -- {sentences:[{text,translation,tokens:[{t,gloss,new}]}]}
    new_words    JSONB       NOT NULL DEFAULT '[]'::jsonb,
    structures   JSONB       NOT NULL DEFAULT '[]'::jsonb,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_readings_user_lang
    ON readings (user_id, language_id, created_at DESC);

ALTER TABLE readings ENABLE ROW LEVEL SECURITY;

CREATE POLICY readings_select_own ON readings
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY readings_insert_own ON readings
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY readings_delete_own ON readings
    FOR DELETE TO authenticated USING (user_id = auth.uid());

CREATE TABLE IF NOT EXISTS grammar_gap_log (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id  UUID        NOT NULL REFERENCES languages(id),
    structure    TEXT        NOT NULL,     -- the structure as the generator named it
    example      TEXT,                     -- one sentence from the reading using it
    source       TEXT        NOT NULL DEFAULT 'reader',
    count        INT         NOT NULL DEFAULT 1,   -- how often it has surfaced
    status       TEXT        NOT NULL DEFAULT 'new'
                             CHECK (status IN ('new', 'planned', 'covered', 'dismissed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (language_id, structure)
);

-- Operator data, never user-visible: RLS on with no policies (privileged
-- connection only), same pattern as tts_audio.
ALTER TABLE grammar_gap_log ENABLE ROW LEVEL SECURITY;
