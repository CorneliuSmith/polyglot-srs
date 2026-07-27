-- Hebrew (he), Latin (la), Persian (fa), Indonesian (id), Tagalog (tl):
-- draft tier (WP76), same starter-scale precedent as hi/jam/nl/th/ko.
--
-- Each rides AccentFoldingNLP (article/particle handling per-language,
-- niqqud/harakat folding for he/fa) with a hand-authored starter vocab +
-- grammar set — smaller than the full generic-pipeline languages, shipped
-- honestly as draft tier. Keyboards, transliteration, Letters & Sounds,
-- and TTS are deferred follow-up work, matching how hi/th/ko originally
-- shipped without them.
--
-- he and fa are rtl=true; la/id/tl are ltr.
--
-- DO NOTHING, not DO UPDATE: this only sets the INITIAL policy for a
-- language that doesn't exist yet — a re-apply must never clobber an
-- admin's later policy change back to 'ai_ok'.
INSERT INTO languages (code, name, rtl, grammar_review_policy) VALUES
    ('he', 'Hebrew', true, 'ai_ok'),
    ('la', 'Latin', false, 'ai_ok'),
    ('fa', 'Persian', true, 'ai_ok'),
    ('id', 'Indonesian', false, 'ai_ok'),
    ('tl', 'Tagalog', false, 'ai_ok')
ON CONFLICT (code) DO NOTHING;
