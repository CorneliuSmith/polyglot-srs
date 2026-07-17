-- WP22: localized grammar explanations for English-from-X learners.
--
-- A beginner learning English FROM Russian cannot read an English-only
-- explanation of English articles. This table carries the explanation in
-- the learner's support locale, written L1-aware (what articles ARE gets
-- explained differently to a Russian speaker than to a Spanish speaker).
-- Same COALESCE rule as definitions and drill hints: locale row wins,
-- authored English is the fallback.

CREATE TABLE IF NOT EXISTS explanation_translations (
    grammar_point_id UUID    NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    locale           TEXT    NOT NULL,
    explanation      TEXT    NOT NULL,
    reviewed         BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (grammar_point_id, locale)
);

ALTER TABLE explanation_translations ENABLE ROW LEVEL SECURITY;

-- Learner-visible content: readable by any signed-in user; writes happen
-- via the privileged seeder/reviewer paths only.
CREATE POLICY explanation_translations_read ON explanation_translations
    FOR SELECT TO authenticated USING (true);
