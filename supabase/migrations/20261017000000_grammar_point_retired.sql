-- Retiring a grammar point without orphaning the learner who studied it.
--
-- Korean teaches four topics twice. Two readers of Korean compared each pair
-- against `docs/quality/ko.md` and the drills themselves (8 Sep 2026); five
-- points lose. They cannot simply leave `data/grammar/ko_grammar.json`:
-- `seed_grammar` is add-only for points — it updates what the file has and
-- inserts what is new, and a point the file stops mentioning stays in
-- production for ever. Vocabulary had exactly this gap until migration
-- 20261016.
--
-- Nor can the row be deleted. `user_cards.card_id` references a grammar
-- point, the card draw INNER JOINs it, and `gym_progress` hangs off its
-- drills — so a delete empties a learner's session and takes their history
-- with it.
--
-- So the row stays and stops being drawn. A retired point:
--   * is not offered in Learn, not drawn in Review, and not listed on the
--     grammar path or in the Gym,
--   * keeps its `user_cards` row, its schedule and its history, so a learner
--     who was part-way through it loses nothing,
--   * takes its drills out of view with it, since nothing draws a drill
--     except through its point.
--
-- Nullable rather than a boolean, for the same reason as vocabulary: the
-- timestamp says WHEN, which is what a reader needs when a card disappears
-- and someone asks why. `reconcile` sets it from
-- `data/grammar_exclusions.tsv` and clears it for any point that leaves the
-- file, so the file stays the single source of truth (quality rule 27).
--
-- Readers probe for this column and treat its absence as "nothing retired",
-- so a deploy ahead of its schema serves the old behaviour rather than 500s
-- on the hot path (CLAUDE.md).

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS retired_at TIMESTAMPTZ;

-- Every grammar draw filters on it, so it needs to be cheap. A partial
-- index: retired points are the rare case and the common query asks for the
-- ones that are NOT retired.
CREATE INDEX IF NOT EXISTS grammar_points_active_idx
    ON grammar_points (language_id)
    WHERE retired_at IS NULL;
