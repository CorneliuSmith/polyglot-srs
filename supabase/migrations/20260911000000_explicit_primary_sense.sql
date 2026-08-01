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
-- Across the shipped frequency lists this releases 97 of 431 words.
--
-- Safe to run whether or not anything has changed since 20260910: it
-- recomputes both columns from scratch rather than toggling them.

-- Primary sense: everything before the first semicolon, minus a leading
-- "(label)". Postgres has no inline helper here, so it is spelled out.
UPDATE vocabulary v SET is_explicit = COALESCE((
    SELECT bool_or(
        regexp_replace(split_part(t.definition, ';', 1), '^\s*\([^)]*\)\s*', '')
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
    )
    FROM translations t
    WHERE t.vocabulary_id = v.id
), false);

-- Sentences are prose, not sense lists: there is no "primary sense" of a
-- sentence, so they are still judged whole. The mild guard does not apply
-- either — a sentence is not labelled by a lexicographer.
UPDATE example_sentences SET is_explicit =
    coalesce(translation, '') ~* ('\y(' ||
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

-- An explicit word's examples go with it, re-applied after the reset above.
UPDATE example_sentences es SET is_explicit = true
WHERE NOT es.is_explicit
  AND EXISTS (
      SELECT 1 FROM vocabulary v
      WHERE v.id = es.vocabulary_id AND v.is_explicit
  );
