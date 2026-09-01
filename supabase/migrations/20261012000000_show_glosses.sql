-- Word-by-word glosses as an account setting (owner: "make glosses an
-- option that is turned on automatically in the user account", then "make
-- the gloss off by default").
--
-- A gloss is a Leipzig morphological decomposition — `bark.3SG`,
-- `have.NEG`. It shows how a sentence is BUILT, which is genuinely useful
-- and genuinely unfamiliar: learners reported it as confusing and as not
-- enough to guess a word from.
--
-- Default OFF. The layer stays available to anyone who wants it — the
-- Settings toggle carries an explanation of the notation, which is where
-- someone decides — but a learner who has never met interlinear glossing
-- is not handed `bark.3SG` unasked as one of their hints. The reports that
-- prompted this were from people meeting it without context.
--
-- Account-level, not device-level — the same lesson the sentence-audio
-- setting recorded (20261001): a setting that lives on the device lets two
-- devices disagree about one account, which the owner hit with the
-- interface language.
--
-- Reads degrade to the default when this migration has not been applied
-- (see `_present_profile_columns` in backend/routers/auth.py). That guard
-- is not optional here: /auth/profile is fetched on every page load, so an
-- unguarded new column on this table takes the whole app down rather than
-- one setting.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS show_glosses BOOLEAN NOT NULL DEFAULT false;
