-- Migration: Example sentences
-- Graded example sentences attached to vocabulary words (Tatoeba-sourced).
-- difficulty_rank = frequency rank of the sentence's rarest word, so the app
-- can serve "i+1" examples: sentences entirely within the learner's level
-- except the word being studied. Content table — readable by all
-- authenticated users, no RLS (same policy as vocabulary/translations).

CREATE TABLE example_sentences (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id     UUID        NOT NULL REFERENCES languages(id),
    vocabulary_id   UUID        NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    sentence        TEXT        NOT NULL,
    translation     TEXT,
    difficulty_rank INT,
    source          TEXT        NOT NULL DEFAULT 'tatoeba',
    license         TEXT        NOT NULL DEFAULT 'CC BY 2.0 FR',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vocabulary_id, sentence)
);

CREATE INDEX idx_example_sentences_vocab_difficulty
    ON example_sentences (vocabulary_id, difficulty_rank);

CREATE INDEX idx_example_sentences_language_difficulty
    ON example_sentences (language_id, difficulty_rank);
