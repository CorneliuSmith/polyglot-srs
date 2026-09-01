-- Word-by-word glosses as an account setting (owner: "make glosses an
-- option that is turned on automatically in the user account").
--
-- A gloss is a Leipzig morphological decomposition — `bark.3SG`,
-- `have.NEG`. It shows how a sentence is BUILT, which is genuinely useful
-- and genuinely unfamiliar: learners reported it as confusing and as not
-- enough to guess a word from. The answer is not to hide it from everyone
-- or to fuse it to the translation, but to let a learner who does not want
-- it turn it off.
--
-- Default ON, per the request's own wording: the layer is the default and
-- the toggle is the escape. Every learner keeps what they have today
-- unless they choose otherwise.
--
-- Account-level, not device-level — the same lesson the sentence-audio
-- setting recorded (20261001): a setting that lives on the device lets two
-- devices disagree about one account, which the owner hit with the
-- interface language.
--
-- Reads degrade to the default when this migration has not been applied
-- (see _OPTIONAL_PROFILE_COLUMNS in backend/routers/auth.py). That guard
-- is not optional here: /auth/me is fetched on every page load, so an
-- unguarded new column on this table takes the whole app down rather than
-- one setting.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS show_glosses BOOLEAN NOT NULL DEFAULT true;
