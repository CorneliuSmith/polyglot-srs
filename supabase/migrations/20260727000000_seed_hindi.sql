-- Hindi (hi): the 18th language. Devanagari script, transliteration hint
-- layer (romanized reading per vocabulary row), full corpus pipeline support
-- (HermitDave 2018 hi_full + kaikki Hindi + Tatoeba hin), a Devanagari QWERTY
-- IME, and an hi-IN neural TTS voice.
--
-- Draft tier: the 42-point grammar path (A1→C2) is authored here, not yet
-- natively reviewed, so Hindi ships with grammar_review_policy = 'ai_ok' —
-- the same visibility model as sw/mi/ha/xh/yo. The points stay reviewed =
-- false (a native Hindi reviewer will see them flagged as drafts); a
-- companion post-seed step marks their ai_check_status = 'pass' so they are
-- studyable now. Vocabulary has no review gate and shows immediately.
-- DO NOTHING, not DO UPDATE: this only sets the INITIAL policy for a language
-- that doesn't exist yet. A re-apply (e.g. a migration-catchup run against a
-- DB that was hand-migrated out of band) must never clobber an admin's later
-- policy change back to 'ai_ok' — that silently undid real admin settings.
INSERT INTO languages (code, name, rtl, grammar_review_policy)
VALUES ('hi', 'Hindi', false, 'ai_ok')
ON CONFLICT (code) DO NOTHING;
