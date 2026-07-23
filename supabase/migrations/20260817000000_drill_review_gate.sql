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

-- created_by: the learner who triggered an on-demand generation. Such a drill
-- is served to THAT learner immediately (their Gym), but stays private to them
-- until a reviewer approves it for everyone (reviewed → true). Null for seed/
-- human/imported drills and for admin-batch generation (those are pending for
-- everyone until reviewed).
ALTER TABLE drill_sentences
    ADD COLUMN created_by UUID REFERENCES auth.users(id) ON DELETE SET NULL;

-- Learner-facing serving filters on reviewed (or created_by = auth.uid()); the
-- review queue reads the pending 'ai' rows.
CREATE INDEX idx_drill_sentences_point_reviewed
    ON drill_sentences (grammar_point_id, reviewed);
CREATE INDEX idx_drill_sentences_created_by
    ON drill_sentences (created_by);
