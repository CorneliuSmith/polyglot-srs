-- Migration: explicit content is opt-in, not default
--
-- A learner reported meeting "whore" in their vocabulary. Nobody chose to
-- teach them that: the frequency lists are built from subtitle and web
-- corpora, which are honest about how people actually speak, and Spanish
-- *puta* is rank 505 — inside the first thousand words a beginner sees. The
-- harvested sentence corpus supplied "Fucking whore." as its example.
--
-- This is not a decision to censor the languages. These words are frequent
-- for a reason, adult learners reading real material will meet them, and a
-- learner who asks for them should get them. It IS a decision that they
-- should not arrive unannounced in week two of an app someone might be using
-- on a commute or handing to a teenager. Hence a flag and a setting, not a
-- delete.
--
-- Default false on BOTH sides: content is assumed clean until marked, and
-- learners are assumed not to have opted in. The filter can only ever hide
-- less than intended if the backfill misses something, never more.

-- The learner's choice. Off by default; Settings has the toggle.
ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS allow_explicit_content BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE vocabulary
    ADD COLUMN IF NOT EXISTS is_explicit BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS is_explicit BOOLEAN NOT NULL DEFAULT false;

-- Partial indexes: the filtered read is "give me the NOT explicit rows",
-- which is almost all of them, so index the rare side for the counts and the
-- admin review of what got hidden.
CREATE INDEX IF NOT EXISTS idx_vocabulary_explicit
    ON vocabulary (language_id) WHERE is_explicit;
CREATE INDEX IF NOT EXISTS idx_example_sentences_explicit
    ON example_sentences (vocabulary_id) WHERE is_explicit;

-- Backfill. This mirrors SQL_EXPLICIT_PATTERN in
-- backend/services/content_filter.py — the two must agree, and the Python
-- side carries the reasoning for what is in the list and what is
-- deliberately left out (mild profanity, clinical anatomy, and "cock",
-- which glosses the rooster across half the catalogue).
--
-- Matching runs on the ENGLISH side because every row has one and the
-- catalogue spans twenty-odd languages whose profanity we cannot enumerate.
-- A lexicographer who wrote "whore, slut, prostitute" as the gloss has
-- already done the classification.
--
-- \y is Postgres's word boundary; ~* is case-insensitive match.
-- The gloss lives in `translations`, not on `vocabulary` — one row per
-- locale. Any locale matching marks the word: a term flagged as vulgar in
-- its Spanish gloss is the same term whichever language a learner reads it
-- in.
UPDATE vocabulary v SET is_explicit = true
WHERE NOT v.is_explicit
  AND EXISTS (
    SELECT 1 FROM translations t
    WHERE t.vocabulary_id = v.id
      AND t.definition ~* ('\y(' ||
        'whore|whores|whoring|whorehouse|whorehouses|' ||
        'slut|sluts|slutty|prostitute|prostitutes|prostitution|' ||
        'hooker|hookers|brothel|brothels|pimp|pimps|' ||
        'fuck|fucks|fucked|fucking|fucker|fuckers|' ||
        'shit|shits|shitty|shitting|bullshit|' ||
        'cunt|cunts|twat|twats|bitch|bitches|bastard|bastards|' ||
        'wanker|wankers|bollocks|arsehole|asshole|assholes|' ||
        'dickhead|prick|pricks|dick|dicks|tits|titties|' ||
        'blowjob|blowjobs|handjob|cum|jizz|wank|' ||
        'masturbate|masturbation|masturbating|' ||
        'porn|porno|pornography|pornographic|orgasm|orgasms|' ||
        'faggot|faggots' ||
      ')\y|vulgar|obscene|profanity|expletive|taboo word|swear ?word')
  );

UPDATE example_sentences SET is_explicit = true
WHERE NOT is_explicit
  AND coalesce(translation, '') ~* ('\y(' ||
        'whore|whores|whoring|whorehouse|whorehouses|' ||
        'slut|sluts|slutty|prostitute|prostitutes|prostitution|' ||
        'hooker|hookers|brothel|brothels|pimp|pimps|' ||
        'fuck|fucks|fucked|fucking|fucker|fuckers|' ||
        'shit|shits|shitty|shitting|bullshit|' ||
        'cunt|cunts|twat|twats|bitch|bitches|bastard|bastards|' ||
        'wanker|wankers|bollocks|arsehole|asshole|assholes|' ||
        'dickhead|prick|pricks|dick|dicks|tits|titties|' ||
        'blowjob|blowjobs|handjob|cum|jizz|wank|' ||
        'masturbate|masturbation|masturbating|' ||
        'porn|porno|pornography|pornographic|orgasm|orgasms|' ||
        'faggot|faggots' ||
      ')\y|vulgar|obscene|profanity|expletive|taboo word|swear ?word');

-- An explicit word's example sentences go with it: the sentence may read
-- clean on its own while existing only to demonstrate the word.
UPDATE example_sentences es SET is_explicit = true
WHERE NOT es.is_explicit
  AND EXISTS (
      SELECT 1 FROM vocabulary v
      WHERE v.id = es.vocabulary_id AND v.is_explicit
  );
