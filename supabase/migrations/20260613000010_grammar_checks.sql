-- Migration: Grammar content checks (semantic review)
-- The NLP layer only proves a drill is *answerable*. Semantic correctness — is
-- the grammar right, the explanation accurate, the sentence natural — needs
-- judgment, so a point now carries two more gates beyond the mechanical check:
--   ai_check_*   : an advisory AI linguist review (pass | concerns + notes)
--   reviewed_by / reviewed_at : the REQUIRED human linguist sign-off (who/when)
-- Only human-reviewed grammar is served to learners (see add_grammar_learn_batch).

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS ai_check_status TEXT
        CHECK (ai_check_status IN ('pass', 'concerns')),
    ADD COLUMN IF NOT EXISTS ai_check_notes  TEXT,
    ADD COLUMN IF NOT EXISTS ai_checked_at   TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reviewed_by     UUID REFERENCES auth.users(id),
    ADD COLUMN IF NOT EXISTS reviewed_at     TIMESTAMPTZ;
