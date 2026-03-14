-- Migration: Add unique constraint on vocabulary(language_id, word)
-- Required for seed script UPSERT idempotency via ON CONFLICT (language_id, word)

ALTER TABLE vocabulary ADD CONSTRAINT vocabulary_language_word_unique UNIQUE (language_id, word);
