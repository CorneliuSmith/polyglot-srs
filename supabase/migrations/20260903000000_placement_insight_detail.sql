-- What the placement test LEARNED, not just what it concluded (owner:
-- "gym, tutor, read should have insights into test results", 2026-07-28).
--
-- 20260902 recorded the verdict — a CEFR letter — and threw away the
-- evidence. But the verdict is the least useful part: "B1" tells the Tutor
-- where to pitch itself and nothing else. The per-level tally says where the
-- learner's ceiling actually is (passed A1/A2 clean, 1 of 3 at B1), and the
-- missed items name the exact structures and words they got wrong.
--
-- That evidence matters most on day one, which is precisely when the app has
-- none of its own: a brand-new learner has no review log and no gym_progress,
-- so every AI surface drills blind. The placement test is the only graded
-- data that exists at that moment.
--
-- Added separately from 20260902 rather than edited into it: that file may
-- already be applied, and a migration that has run is not ours to rewrite.
ALTER TABLE placement_attempts
    ADD COLUMN IF NOT EXISTS per_level JSONB NOT NULL DEFAULT '{}'::jsonb,
    -- drill_sentences the learner missed. No FK: these are a historical
    -- record of one sitting, and a drill later retired by a reviewer must
    -- not delete the evidence that this learner missed it.
    ADD COLUMN IF NOT EXISTS missed_grammar_ids UUID[] NOT NULL DEFAULT '{}',
    ADD COLUMN IF NOT EXISTS missed_vocabulary_ids UUID[] NOT NULL DEFAULT '{}';
