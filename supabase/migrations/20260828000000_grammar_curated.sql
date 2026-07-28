-- Grammar re-seed protection (extends the vocabulary Option B to grammar).
--
-- Re-seeding a language's grammar file used to overwrite every point's text
-- (and reset its `reviewed` approval), and DELETE+rebuild every point's drills
-- — which, via gym_progress's ON DELETE CASCADE, also erased each learner's
-- per-drill Gym history on every re-seed. Two fixes land together:
--
--   1. The seeder now diff-syncs drills in place (stable ids → gym_progress
--      survives) instead of deleting them — no schema change needed for that.
--   2. A `curated` flag marks a grammar point a human has touched (approved,
--      edited, or whose drills were hand-managed). The seeder never overwrites
--      a curated point: proposed text changes go to content_suggestions
--      (source='extraction', same accept/dismiss queue and AI-doc badge as
--      vocabulary), and new drills land source='ai'/reviewed=false in the
--      pending-drills queue.
--
-- Backfill: reviewed_by distinguishes a real in-app reviewer sign-off from
-- hand-authored seed files that shipped reviewed=true with no reviewer — only
-- the former marks the point human-owned.

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS curated BOOLEAN NOT NULL DEFAULT false;

UPDATE grammar_points SET curated = true
 WHERE reviewed = true AND reviewed_by IS NOT NULL;

-- The re-seed looks curated points up per language before touching anything.
CREATE INDEX IF NOT EXISTS idx_grammar_points_curated
    ON grammar_points (language_id) WHERE curated;
