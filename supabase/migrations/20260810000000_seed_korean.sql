-- Korean (ko): language 22, draft tier (WP27).
--
-- Rides the full generic pipeline (HermitDave ko_50k + kaikki Korean +
-- Tatoeba kor): 7k words, ~3.8k example sentences, 40-point A1→C2 path
-- (240 drills) covering particles, the 요/ㅂ니다/한다 register ladder,
-- honorifics both directions, the ㅂ/ㄷ/르 irregular families, and the
-- quotation system. KoreanNLP does particle stripping + conservative
-- de-conjugation. Ships grammar_review_policy='ai_ok' with points
-- reviewed=false + ai_check pass, same as the hi/jam/nl/th draft
-- precedent — native reviewers promote to strict at the reviewer-program
-- milestone.
INSERT INTO languages (code, name, rtl, grammar_review_policy) VALUES
    ('ko', 'Korean', false, 'ai_ok')
ON CONFLICT (code) DO UPDATE SET grammar_review_policy = EXCLUDED.grammar_review_policy;
