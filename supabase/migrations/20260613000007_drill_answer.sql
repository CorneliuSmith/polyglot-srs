-- Migration: drill sentence answers
-- Fill-in-the-blank grammar drills need the target answer stored explicitly.
-- Until now grammar cards fell back to the grammar point's title as a
-- placeholder answer; this stores the actual inflected form that fills the
-- {{answer}} blank, so grammar review can validate real answers.

ALTER TABLE drill_sentences
    ADD COLUMN IF NOT EXISTS answer TEXT;

-- Unique titles per language so the grammar seeder can UPSERT points
-- idempotently (re-running a curriculum file updates in place).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'grammar_points_language_title_key'
    ) THEN
        ALTER TABLE grammar_points
            ADD CONSTRAINT grammar_points_language_title_key UNIQUE (language_id, title);
    END IF;
END$$;
