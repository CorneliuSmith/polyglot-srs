-- Dutch (nl) and Thai (th): languages 20 and 21, draft tier.
--
-- Dutch rides the full generic pipeline (HermitDave + kaikki + Tatoeba nld)
-- with a 42-point A1→C2 path. Thai is the app's first space-less script:
-- the sentence pipeline segments Tatoeba tha with a greedy longest-match
-- lexicon segmenter; 40-point path incl. classifiers, particles, and the
-- royal register. Both ship grammar_review_policy='ai_ok' with points
-- reviewed=false + ai_check pass, same as the hi/jam draft precedent —
-- native reviewers promote to strict at the reviewer-program milestone.
INSERT INTO languages (code, name, rtl, grammar_review_policy) VALUES
    ('nl', 'Dutch', false, 'ai_ok'),
    ('th', 'Thai',  false, 'ai_ok')
ON CONFLICT (code) DO UPDATE SET grammar_review_policy = EXCLUDED.grammar_review_policy;
