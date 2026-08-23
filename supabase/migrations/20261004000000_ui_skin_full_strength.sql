-- The A/B/C/D directions at full strength (owner: "I am not getting the
-- full ui versions that we made").
--
-- The variants themselves are unchanged — same keys, same letters, every
-- assignment survives — but the description both audiences read (the admin
-- panel and an assigned tester's Settings card) said C and D "show mostly
-- in study sessions", which stopped being true of C when Language as
-- Ground took over the whole page. Description only; enabled/rollout/
-- default stay untouched for the same reason as ever: a re-applied
-- migration must never flip a live experiment.

UPDATE experiments
   SET description = 'Which look the app is wearing. Classic is what '
         'shipped; A, B, C and D are four visual directions being tried '
         'out. A (a book about a language), B (ink grid) and C (the '
         'language as the room) restyle every page; D quiets everything '
         'but the card during study sessions.',
       updated_at = now()
 WHERE key = 'ui_skin';
