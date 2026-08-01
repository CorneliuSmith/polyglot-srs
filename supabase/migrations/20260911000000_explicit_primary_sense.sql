-- Migration: reclassify explicit content on the primary sense only
--
-- Correcting 20260910, which I got wrong. That backfill matched the explicit
-- word list ANYWHERE in a gloss. Dictionary glosses lead with the primary
-- sense and push the rest behind a semicolon, so it hid a set of perfectly
-- ordinary, high-frequency words over a register listed fourth:
--
--   es  maldito   rank  583  "cursed; damned, freaking, fucking"
--   hi  गंदगी      rank  471  "filth, dirt; a vulgarity, expletive"
--   tr  herif     rank  393  "comrade, colleague; a term of contempt"
--   jam baxide    rank  361  "wow! (MILD expletive)"
--
-- *maldito* means "cursed". *गंदगी* means dirt. Hiding those is the failure
-- mode the filter was explicitly supposed to avoid — a wrongly-hidden word
-- is invisible to the learner and therefore unreportable, which is worse
-- than a slur that slips through and can be flagged.
--
-- The rule now: only the LEADING sense decides, a gloss that calls itself
-- "mild" is left alone, and a leading register label ("(dated) cunt") is
-- stripped rather than mistaken for the whole sense. Mirrors
-- backend/services/content_filter.py; the two must agree.
--
-- ---------------------------------------------------------------------------
-- WHY THIS ONLY TOUCHES ALREADY-FLAGGED ROWS
--
-- The first version of this migration recomputed is_explicit for EVERY
-- vocabulary row — an unconditional UPDATE over ~157k rows, each running a
-- correlated regex against its translations, rewriting all of them (plus two
-- partial indexes and the WAL) to change about a hundred. It hit Supabase's
-- statement timeout and rolled back.
--
-- It never needed to look at more than the flagged rows. The new rule is a
-- STRICT NARROWING of the old one:
--
--   * the primary sense is a substring of the whole gloss, so anything
--     matching in the primary sense already matched "anywhere";
--   * the "mild" guard only ever removes a match.
--
-- So the new true-set is a subset of the old one: no row that is currently
-- false can become true, and the only work is unflagging. That relies on
-- 20260910 having run first, which it always has — migrations apply in
-- filename order, and this file sorts after it.
--
-- Idempotent: re-running finds nothing left to unflag.

-- Generous ceiling rather than the default. The work below is small, but a
-- migration that silently depends on the server's timeout being big enough
-- is how the first attempt failed.
SET LOCAL statement_timeout = '5min';

-- Vocabulary: unflag anything whose PRIMARY sense doesn't carry it.
-- Only currently-flagged rows are examined (see above).
UPDATE vocabulary v SET is_explicit = false
WHERE v.is_explicit
  AND NOT EXISTS (
      SELECT 1
      FROM translations t
      WHERE t.vocabulary_id = v.id
        -- Primary sense: up to the first semicolon, minus a leading
        -- "(label)" so "(dated) cunt" is read as its sense, not its label.
        AND regexp_replace(split_part(t.definition, ';', 1),
                           '^\s*\([^)]*\)\s*', '')
            ~* ('\y(' ||
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
        -- ...unless the lexicographer already said the sense is mild.
        AND t.definition !~* '\ymild(ly)?\y'
  );

-- Example sentences are judged WHOLE — a sentence has no primary sense — so
-- the rule for them is unchanged from 20260910 and their own flags stand.
-- What does change is INHERITANCE: a sentence flagged only because its
-- headword was flagged must be released when that headword is.
UPDATE example_sentences es SET is_explicit = false
WHERE es.is_explicit
  AND coalesce(es.translation, '') !~* ('\y(' ||
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
  AND NOT EXISTS (
      SELECT 1 FROM vocabulary v
      WHERE v.id = es.vocabulary_id AND v.is_explicit
  );
