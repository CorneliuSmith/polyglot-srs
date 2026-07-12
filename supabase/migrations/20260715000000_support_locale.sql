-- English-as-target support (WP5/WP12): learners studying ENGLISH pick the
-- language their hints render in ("I'm learning English from Spanish").
--
-- example_sentences.translation_locale: which language a sentence's
-- translation is written in. Existing rows are all English glosses of
-- target-language sentences, so the default backfills them correctly.
-- English example sentences carry per-locale translations (es/fr/de/...)
-- and the card queries pick the learner's support locale.
ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS translation_locale TEXT NOT NULL DEFAULT 'en';

-- The learner's chosen support language (NULL = English, today's behavior).
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS support_locale TEXT;

CREATE INDEX IF NOT EXISTS idx_example_sentences_vocab_locale
    ON example_sentences (vocabulary_id, translation_locale);

-- The same English sentence may carry translations in several locales (one
-- row per locale), so the uniqueness key widens to include the locale.
ALTER TABLE example_sentences
    DROP CONSTRAINT IF EXISTS example_sentences_vocabulary_id_sentence_key;
CREATE UNIQUE INDEX IF NOT EXISTS uq_example_sentences_vocab_sentence_locale
    ON example_sentences (vocabulary_id, sentence, translation_locale);
