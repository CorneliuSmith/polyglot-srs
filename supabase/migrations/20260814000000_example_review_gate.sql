-- Review gate for AI-generated example sentences (WP42 follow-up).
--
-- Unlike drills (gated by the grammar point's `reviewed` flag), example
-- sentences are a plain content table served straight to learners. That means
-- an admin-generated ('ai') example would reach learners the moment it passed
-- the automated maker-checker, with no human in the loop. This adds a per-row
-- gate: generated examples land reviewed=false (hidden from learners) until a
-- human approves them; a rejected one is deleted.
--
-- Everything that already exists (seed, tatoeba, human) is trusted content, so
-- the column defaults true and the backfill leaves current rows visible. Only
-- add_example_sentence(source='ai') inserts reviewed=false going forward.

ALTER TABLE example_sentences
    ADD COLUMN reviewed BOOLEAN NOT NULL DEFAULT true;

-- Learner-facing reads filter on reviewed; this keeps that fast, and also
-- speeds the admin "pending review" list (reviewed = false).
CREATE INDEX idx_example_sentences_vocab_reviewed
    ON example_sentences (vocabulary_id, reviewed);
