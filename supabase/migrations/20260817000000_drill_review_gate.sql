-- Review gate for AI-generated grammar drills (WP).
--
-- Generated example SENTENCES already wait behind a reviewed flag; generated
-- DRILLS did not — they went straight into the Gym/learn pool. This adds the
-- same gate: a generated ('ai') drill lands reviewed=false (hidden from
-- learners) until a reviewer approves it in the Contributor › Review tab, at
-- which point it becomes permanent corpus. Rejecting deletes it.
--
-- Everything already in the pool (seed / human / imported) is trusted content,
-- so the column defaults true and the backfill leaves current drills visible.
-- Only add_drill(source='ai') inserts reviewed=false going forward.

ALTER TABLE drill_sentences
    ADD COLUMN reviewed BOOLEAN NOT NULL DEFAULT true;

-- Learner-facing serving filters on reviewed; the review queue reads the
-- pending 'ai' rows.
CREATE INDEX idx_drill_sentences_point_reviewed
    ON drill_sentences (grammar_point_id, reviewed);
