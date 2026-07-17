-- Jamaican Patois (jam): the 19th language, draft tier.
--
-- Latin script in the Cassidy/JLU phonemic orthography, with the common
-- English-based spellings loaded as answer alternatives (likkle/likl,
-- pickney/pikni) so either convention grades as correct. Curated vocabulary
-- (no public frequency corpus exists) + a 32-point grammar path.
--
-- Draft tier on purpose: grammar_review_policy = 'ai_ok' with every point
-- reviewed = false. The beta rollout plan gates promotion out of draft on a
-- JLU-connected native reviewer (friends/family beta → online reviewers).
-- No TTS: no neural Jamaican Patois voice exists anywhere yet.
INSERT INTO languages (code, name, rtl, grammar_review_policy)
VALUES ('jam', 'Jamaican Patois', false, 'ai_ok')
ON CONFLICT (code) DO UPDATE SET grammar_review_policy = EXCLUDED.grammar_review_policy;
