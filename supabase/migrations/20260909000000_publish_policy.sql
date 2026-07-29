-- Migration: four-way publish policy per language
--
-- grammar_review_policy was a two-value switch ('strict' | 'ai_ok') and its
-- CHECK constraint enforced exactly that. The owner needs the line drawn in
-- more places than two: human-reviewed only, human OR AI, human AND AI, or
-- everything-including-unchecked while a language is being built out.
--
-- 'strict' is NOT rewritten to 'human_only'. Renaming a stored value costs a
-- rewrite of every row and buys nothing — backend/services/visibility.py
-- normalises it on read, and the SQL gates treat any unrecognised value as
-- the strictest option, so a legacy row fails closed by construction.

ALTER TABLE languages DROP CONSTRAINT IF EXISTS languages_grammar_review_policy_check;

ALTER TABLE languages
    ADD CONSTRAINT languages_grammar_review_policy_check
    CHECK (grammar_review_policy IN ('strict', 'human_only', 'ai_ok', 'both', 'all'));
