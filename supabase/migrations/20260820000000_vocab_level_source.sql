-- How a word's CEFR level was decided — so an AI estimate is never mistaken
-- for an objective, frequency-derived level.
--
--   frequency — banded from the word's corpus frequency rank (the seed default,
--               objective).
--   curated   — a human set or confirmed it.
--   ai        — the model estimated it; PROVISIONAL until a reviewer confirms.
--
-- Deck placement follows `level` directly (a "B1 Vocabulary" deck is every word
-- with level='B1'), so confirming/adjusting the level is also what places the
-- word in the right deck. A provisional ('ai') level is hidden from learners'
-- decks under the Strict policy and shown under Open ('ai_ok') — same gate as
-- generated drills/examples.

ALTER TABLE vocabulary
    ADD COLUMN level_source TEXT NOT NULL DEFAULT 'frequency'
        CHECK (level_source IN ('frequency', 'curated', 'ai'));

-- Provisional AI levels are read a lot (the learnable-pool gate); index them.
CREATE INDEX idx_vocabulary_language_level_source
    ON vocabulary (language_id, level_source);
