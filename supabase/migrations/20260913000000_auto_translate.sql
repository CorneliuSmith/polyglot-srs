-- Automatic support-locale translation, per LEARNING language.
--
-- When ON for a language, the in-process auto-translate loop
-- (backend/services/auto_translate.py) fills missing support-locale glosses
-- for that course — but only for (course, locale) pairs that real accounts
-- actually use (user_profiles.support_locale), most-subscribed pair first.
-- Nothing is pre-seeded; a pair with no learners costs nothing.
--
-- Default OFF: enabling a language is an admin decision with a real API
-- cost attached, made from the language-management panel. The loop draws on
-- the operator's Anthropic key, never on any learner's usage allowance.

ALTER TABLE languages
    ADD COLUMN IF NOT EXISTS auto_translate_enabled BOOLEAN NOT NULL DEFAULT false;
