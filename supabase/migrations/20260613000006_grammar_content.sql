-- Migration: Grammar & usage content for the review "show grammar" panel
-- Adds the fields the review detail panel surfaces when a learner chooses to
-- review a card, and provenance so explanations from three sources coexist:
--   explanation_source: 'pending' (none yet) | 'ai' (generated, cached) |
--                       'contributor' (hand-authored by a specialist) |
--                       'wiktionary' (open-source usage notes)
--   reviewed: a human specialist has signed off (contributor content is
--             trusted; AI content starts unreviewed and can be promoted).
-- grammar_points.explanation already exists; this adds the culture note and
-- provenance. Vocabulary gets a lighter usage_note (gender, irregular plural,
-- register caveats) shown in its simpler detail view.

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS culture_note        TEXT,
    ADD COLUMN IF NOT EXISTS explanation_source  TEXT NOT NULL DEFAULT 'pending'
        CHECK (explanation_source IN ('pending', 'ai', 'contributor', 'wiktionary')),
    ADD COLUMN IF NOT EXISTS reviewed            BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE vocabulary
    ADD COLUMN IF NOT EXISTS usage_note          TEXT;
