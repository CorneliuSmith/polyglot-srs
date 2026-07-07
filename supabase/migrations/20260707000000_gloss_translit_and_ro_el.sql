-- Language-aware hint layers + two new languages.
--
-- Sentences gain two optional aids, revealed as graduated hint layers by the
-- review UI according to each language's needs:
--   - transliteration: romanization for non-Latin scripts (ru, ar, el) — the
--     first thing a beginner needs before they can even sound the sentence out.
--   - gloss: a word-by-word interlinear gloss for languages whose syntax does
--     not map onto English word order (mi and the Bantu languages) — shows how
--     the sentence is BUILT, not just what it means.
--
-- Also seeds Romanian and Greek into the languages table.

ALTER TABLE drill_sentences
    ADD COLUMN IF NOT EXISTS gloss           TEXT,
    ADD COLUMN IF NOT EXISTS transliteration TEXT;

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS gloss           TEXT,
    ADD COLUMN IF NOT EXISTS transliteration TEXT;

INSERT INTO languages (code, name, rtl) VALUES
    ('ro', 'Romanian', false),
    ('el', 'Greek',    false)
ON CONFLICT (code) DO NOTHING;
