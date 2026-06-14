-- Migration: Per-language grammar review policy
-- Admins decide, per language, how strict the human-review gate is:
--   strict : only human-reviewed grammar reaches learners (default; safest)
--   ai_ok  : grammar that passed the AI semantic check is also shown to
--            learners, clearly labelled "pending expert review", until a human
--            signs off. Lets a language launch without blocking on review.
-- The label and the gate let you trade launch speed against verification per
-- language, instead of one all-or-nothing rule.

ALTER TABLE languages
    ADD COLUMN IF NOT EXISTS grammar_review_policy TEXT NOT NULL DEFAULT 'strict'
        CHECK (grammar_review_policy IN ('strict', 'ai_ok'));
