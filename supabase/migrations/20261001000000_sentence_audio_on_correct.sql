-- Sentence audio on a correct answer (owner: "read the full sentence audio
-- when users get the answer correct. Accounts should be able to turn this
-- off.")
--
-- Account-level, not device-level, and that is a lesson rather than a
-- preference: the same day this was requested, the owner hit a device/
-- account split (interface language) where two devices disagreed about the
-- same account. Settings that live on the account behave the same
-- everywhere the account is opened.
--
-- Default ON per the request's own phrasing — the feature is the default,
-- the toggle is the escape. Reads degrade to that default when this
-- migration hasn't been applied (see _OPTIONAL_PROFILE_COLUMNS in
-- backend/routers/auth.py).

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS sentence_audio_on_correct BOOLEAN NOT NULL DEFAULT true;
