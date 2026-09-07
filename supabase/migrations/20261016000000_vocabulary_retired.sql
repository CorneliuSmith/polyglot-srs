-- Retiring a word without orphaning the learner who studied it.
--
-- `data/vocab_exclusions.tsv` holds 858 headwords the courses should not
-- teach: alphabet letters glossed as vocabulary, Arabic punctuation, English
-- words WordNet matched to a chemical symbol (`em` is a printer's quad, `er`
-- is erbium), typo-mass rows, and 645 given names nobody can produce from
-- "a male given name". Every one of them is still SERVED, because the file
-- is applied by the loader and no seeder deletes a vocabulary row — and it
-- must not: `user_cards.card_id` references it and `get_due_cards` INNER
-- JOINs, so a delete orphans a learner's progress and empties their session
-- (CHECKS §12, DEBT).
--
-- So the row stays and stops being drawn. A retired word:
--   * is not offered to Learn and not drawn in Review,
--   * keeps its `user_cards` row, its history and its schedule, so a learner
--     who already has it loses nothing and can still see it in their lists,
--   * takes its `translations` rows out of view with it — the Spanish UI was
--     showing "eme" for `em`, the wrong gloss faithfully translated.
--
-- Nullable rather than a boolean: the timestamp says WHEN, which is what a
-- reader needs when a card disappears and someone asks why. `reconcile`
-- sets it from the exclusions file and clears it for any word that leaves
-- the file, so the file stays the single source of truth (quality rule 27).
--
-- Readers probe for this column and treat its absence as "nothing retired",
-- so a deploy ahead of its schema serves the old behaviour rather than 500s
-- on the hot path (CLAUDE.md).

ALTER TABLE vocabulary
    ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ;

-- The draw filters on it on every card query, so it needs to be cheap. A
-- partial index: retired rows are the rare case and the common query asks
-- for the ones that are NOT retired.
CREATE INDEX IF NOT EXISTS vocabulary_active_idx
    ON vocabulary (language_id)
    WHERE retired_at IS NULL;
