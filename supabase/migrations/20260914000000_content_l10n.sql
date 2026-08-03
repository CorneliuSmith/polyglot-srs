-- Content-data localization (WP49): the strings a learner still saw in
-- English even with a support locale set — grammar point titles and notes,
-- and the Gym picker's labels — plus a demand queue so the auto-translate
-- loop fills what a learner is actually looking at first.

-- Grammar point metadata overlay: title (shown on cards, the grammar path,
-- the Gym), culture_note and function_note. Same shape and policy as
-- explanation_translations: draft rows are live immediately (the read path
-- COALESCEs with no reviewed gate); reviewed marks a human pass.
CREATE TABLE IF NOT EXISTS grammar_point_translations (
  grammar_point_id UUID NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
  locale TEXT NOT NULL,
  title TEXT,
  culture_note TEXT,
  function_note TEXT,
  reviewed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (grammar_point_id, locale)
);

ALTER TABLE grammar_point_translations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "grammar_point_translations are readable"
  ON grammar_point_translations;
CREATE POLICY "grammar_point_translations are readable"
  ON grammar_point_translations FOR SELECT TO authenticated USING (true);

-- Gym picker overlay: the manifest lives in data/gym/{code}.json, so rows
-- key on (language_code, point) — `point` is the manifest's grammar-point
-- title, the same join key the manifest endpoint already uses. Only label
-- and usage are translated; `example` is course-language text and stays.
CREATE TABLE IF NOT EXISTS gym_label_translations (
  language_code TEXT NOT NULL,
  locale TEXT NOT NULL,
  point TEXT NOT NULL,
  label TEXT,
  usage_note TEXT,
  reviewed BOOLEAN NOT NULL DEFAULT false,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (language_code, locale, point)
);

ALTER TABLE gym_label_translations ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "gym_label_translations are readable"
  ON gym_label_translations;
CREATE POLICY "gym_label_translations are readable"
  ON gym_label_translations FOR SELECT TO authenticated USING (true);

-- Demand queue: when a card read falls back to English for a learner with a
-- support locale, the read path records what was missing and wakes the loop,
-- which translates demanded rows before its breadth-first sweep. Rows are
-- deleted once processed (whether the rendering was approved or rejected —
-- the per-kind convergence markers handle retry semantics). ref_id is the
-- content row's id per kind ('gym' uses the language id).
CREATE TABLE IF NOT EXISTS translation_demand (
  kind TEXT NOT NULL CHECK (kind IN
    ('word', 'drill', 'explanation', 'grammar_meta', 'example', 'gym')),
  ref_id UUID NOT NULL,
  locale TEXT NOT NULL,
  requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (kind, ref_id, locale)
);

ALTER TABLE translation_demand ENABLE ROW LEVEL SECURITY;

-- Card reads run on the authenticated role (RLS connections), so recording
-- demand needs an INSERT policy. Insert-only: rows carry no content (a kind,
-- an id, a locale), the PK dedupes, the loop's budget caps any spend they
-- can cause, and stale rows are swept. No SELECT/UPDATE/DELETE for clients.
DROP POLICY IF EXISTS "translation_demand is recordable" ON translation_demand;
CREATE POLICY "translation_demand is recordable"
  ON translation_demand FOR INSERT TO authenticated WITH CHECK (true);
