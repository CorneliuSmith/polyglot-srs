-- Dutch (nl) and Thai (th): languages 20 and 21, draft tier.
--
-- Dutch rides the full generic pipeline (HermitDave + kaikki + Tatoeba nld)
-- with a 42-point A1→C2 path. Thai is the app's first space-less script:
-- the sentence pipeline segments Tatoeba tha with a greedy longest-match
-- lexicon segmenter; 40-point path incl. classifiers, particles, and the
-- royal register. Both ship grammar_review_policy='ai_ok' with points
-- reviewed=false + ai_check pass, same as the hi/jam draft precedent —
-- native reviewers promote to strict at the reviewer-program milestone.
-- DO NOTHING, not DO UPDATE: this only sets the INITIAL policy for a language
-- that doesn't exist yet — a re-apply must never clobber an admin's later
-- policy change back to 'ai_ok'.
INSERT INTO languages (code, name, rtl, grammar_review_policy) VALUES
    ('nl', 'Dutch', false, 'ai_ok'),
    ('th', 'Thai',  false, 'ai_ok')
ON CONFLICT (code) DO NOTHING;
