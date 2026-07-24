-- Generalize review notes to cover vocabulary, not just grammar points.
--
-- A reviewer (or trial reviewer) could already file a note on a grammar point
-- — the middle ground between "fix it myself" and "silently don't approve".
-- Words deserve the same: "this gloss is regional", "the B1 level looks high".
-- Rather than a parallel table, point_review_notes grows a nullable
-- vocabulary_id; each note hangs off exactly one of the two entities.

ALTER TABLE point_review_notes
    ALTER COLUMN grammar_point_id DROP NOT NULL,
    ADD COLUMN IF NOT EXISTS vocabulary_id UUID
        REFERENCES vocabulary(id) ON DELETE CASCADE;

-- Exactly one target: a grammar-point note or a vocabulary note, never both,
-- never neither. (num_nonnulls counts the non-NULL arguments.)
ALTER TABLE point_review_notes
    DROP CONSTRAINT IF EXISTS point_review_notes_one_target;
ALTER TABLE point_review_notes
    ADD CONSTRAINT point_review_notes_one_target
        CHECK (num_nonnulls(grammar_point_id, vocabulary_id) = 1);

CREATE INDEX IF NOT EXISTS idx_point_review_notes_vocab_status
    ON point_review_notes (vocabulary_id, status);

-- RLS unchanged: reads/writes go through the privileged connection after the
-- app layer verifies the caller's role for the entity's language.
