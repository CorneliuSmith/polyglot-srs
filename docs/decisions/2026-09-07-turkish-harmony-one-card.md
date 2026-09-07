# 7 September 2026 — Turkish harmony spellings are one card

**Owner:** "personally, I think that terms should be linked but show the
vowel parity that applies."

**Context.** The Phase 2d definition pass found `mi`, `mı`, `mu`, `mü` as four
Turkish headwords sharing "Used to form interrogatives", and repaired each
with a definition naming the vowel class it follows. The owner, who knows
the language: "The turkish fix I saw scares me" — `tr.md` hint standard 2
says state the harmony RULE, never the OUTCOME, and the repair stated the
outcome four times.

**Decision.** One card per morpheme (`mi`, `de`, `ta`); the other spellings
linked through the frequency file's `alt` column → `vocabulary.alternatives`;
the definition states the rule; the card blanks whichever spelling the
sentence carries and expects that one back; typing another spelling is the
right word graded sloppy, with the rule. Korean's 받침 pairs stay two cards —
there the condition can be stated without handing over the answer.

**What it cost.** Python's case-insensitive regex had been folding dotless ı
onto i, so the fix had to give Turkish its own span finder and unify the
four copies of the finder registry; three mis-cased headwords surfaced and
were repaired; two foreign words (`pin`, `instagram`) lost their 3 sentence
rows. Full record: `docs/quality/CHECKS.md` §30, `docs/quality/tr.md`,
`docs/quality/ko.md`. Owner-run: `seeder.run -l tr` before
`reconcile --apply` (`docs/plans/owner-actions-2026-09-07.md`, step 2b).
