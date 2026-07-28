-- Placement evidence as real rows with real foreign keys, replacing the
-- untyped uuid[] columns from 20260903 (owner review, 2026-07-28).
--
-- The arrays were wrong, and the reasoning behind them was inconsistent: the
-- stated goal was "a retired drill must not erase the fact that this learner
-- missed it", but the reader resolved those ids by JOINing live content — so
-- retiring a drill DID erase the evidence, just silently and with a dangling
-- uuid left behind. Skipping the FK bought nothing and cost integrity.
--
-- The actual requirement is two separate things, and they need two different
-- mechanisms:
--
--   1. A LIVE POINTER, so the Gym can aim at the same form again. That wants
--      a foreign key — it should follow edits and never dangle.
--   2. A SNAPSHOT of what the item was called, so the Tutor and Reader can
--      still say "you missed the subjunctive after querer" after the drill
--      that proved it has been retired.
--
-- Delete behaviour is chosen per relationship rather than blanket-avoided:
--   drill_id       ON DELETE SET NULL — the drill was one piece of evidence;
--                  losing it doesn't invalidate the finding (label/cell/level
--                  are snapshotted, so the finding survives intact).
--   vocabulary_id  ON DELETE SET NULL — same reasoning.
--   grammar_point_id ON DELETE CASCADE — the row is ABOUT this point. If the
--                  point is gone there is nothing left to drill, so the row
--                  is genuinely meaningless. The level-grained tally in
--                  placement_attempts.per_level still preserves "you were B1
--                  in March", so deleting a point never rewrites history.
CREATE TABLE IF NOT EXISTS placement_attempt_items (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    attempt_id UUID NOT NULL
        REFERENCES placement_attempts(id) ON DELETE CASCADE,
    kind       TEXT NOT NULL CHECK (kind IN ('grammar', 'vocabulary')),

    -- Live pointers (see delete behaviour above).
    drill_id         UUID REFERENCES drill_sentences(id) ON DELETE SET NULL,
    vocabulary_id    UUID REFERENCES vocabulary(id)      ON DELETE SET NULL,
    grammar_point_id UUID REFERENCES grammar_points(id)  ON DELETE CASCADE,

    -- Snapshot, taken at the moment of the sitting. A grammar point renamed
    -- or a drill retired later cannot rewrite what this learner was asked.
    label TEXT,   -- grammar point title, or the word itself
    cell  TEXT,   -- morphological cell, for the Gym's generator
    level TEXT
);

-- "What did they miss in this attempt?" — the insight read.
CREATE INDEX IF NOT EXISTS idx_placement_items_attempt
    ON placement_attempt_items (attempt_id);
-- "Did they miss this point at placement?" — the Gym's cold-start read,
-- which the array version could only answer with an unindexed array scan.
CREATE INDEX IF NOT EXISTS idx_placement_items_point
    ON placement_attempt_items (grammar_point_id)
    WHERE grammar_point_id IS NOT NULL;

ALTER TABLE placement_attempt_items ENABLE ROW LEVEL SECURITY;

-- Ownership is the parent attempt's — there is no user_id to denormalize
-- and get out of step with.
CREATE POLICY "placement_attempt_items_select_own"
    ON placement_attempt_items FOR SELECT
    USING (EXISTS (
        SELECT 1 FROM placement_attempts pa
        WHERE pa.id = attempt_id AND pa.user_id = auth.uid()
    ));
CREATE POLICY "placement_attempt_items_insert_own"
    ON placement_attempt_items FOR INSERT
    WITH CHECK (EXISTS (
        SELECT 1 FROM placement_attempts pa
        WHERE pa.id = attempt_id AND pa.user_id = auth.uid()
    ));
CREATE POLICY "placement_attempt_items_delete_own"
    ON placement_attempt_items FOR DELETE
    USING (EXISTS (
        SELECT 1 FROM placement_attempts pa
        WHERE pa.id = attempt_id AND pa.user_id = auth.uid()
    ));

-- Carry across anything 20260903 already recorded, then retire the arrays so
-- there is only one source of truth. Guarded: 20260903 may not have run here.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'placement_attempts'
          AND column_name = 'missed_grammar_ids'
    ) THEN
        INSERT INTO placement_attempt_items
            (attempt_id, kind, drill_id, grammar_point_id, label, cell, level)
        SELECT pa.id, 'grammar', ds.id, gp.id, gp.title, ds.cell, gp.level
        FROM placement_attempts pa
        JOIN drill_sentences ds ON ds.id = ANY(pa.missed_grammar_ids)
        JOIN grammar_points gp ON gp.id = ds.grammar_point_id;

        INSERT INTO placement_attempt_items
            (attempt_id, kind, vocabulary_id, label, level)
        SELECT pa.id, 'vocabulary', v.id, v.word, v.level
        FROM placement_attempts pa
        JOIN vocabulary v ON v.id = ANY(pa.missed_vocabulary_ids);
    END IF;
END $$;

ALTER TABLE placement_attempts
    DROP COLUMN IF EXISTS missed_grammar_ids,
    DROP COLUMN IF EXISTS missed_vocabulary_ids;
