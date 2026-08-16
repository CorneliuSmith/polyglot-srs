# Reader quality: correct language, real content, and an honest level dial

The owner's report, from an A1 English reading ("The Maya People"):
the stories are bad two distinct ways, and the level control is too coarse.

1. **The text is ungrammatical.** "They *live* in this area a very long
   time ago", "The Maya *build* this big temple", "every king *rule* one
   city", "it *watch* the sun". This is not A1 English — it is broken
   English. No native A1 text does this; simplified ≠ wrong.
2. **The text is empty.** "Do you know the Maya calendar?", "I think
   their history is amazing" — filler and vibes. Not information dense,
   not informative. A1 constrains the *language*, but the reader is an
   adult: the *content* should still teach something.
3. **The challenge dial is relative only** (Easier / My level / Stretch).
   The owner wants absolute A1–C2 as options.

## Root causes (from `backend/services/reader.py`)

### Why the grammar broke

The closed-cage constraint says: *"Grammar: use ONLY structures the
learner has learned: … the absolute basics (present tense, simple
sentences)"*. Give that cage a historical topic and the model has three
options: refuse the topic, recast it, or write past events in bare
present. It picks the third — and once it has internalized "write
degraded English", agreement errors ("every king rule") follow for free.
The cage forbids structures, but **nothing in the prompt states that
correctness is inviolable**, so constraint-compliance silently outranks
grammaticality.

The contract checker can't catch it: it grades `level_ok`, `length_ok`,
`voice_ok` — a grammatically broken text at the right level PASSES.

### Why the content is thin

The prompt asks for "natural, warm, factually grounded prose" and then
locks vocabulary to A1. Warmth survives the lock; facts don't. Nothing
demands information per sentence, so the model pads with rhetorical
questions and "X is amazing". The checker doesn't grade substance either.

### Why the dial is coarse

`complexity` is `easier|level|stretch` — a ±1 shift on the learner's
resolved level. There is no way to say "write me B2" directly.

## The fixes

### 1. The correctness invariant (prompt, both cages)

A new hard constraint, stated before the cage so it wins:

> Every sentence must be CORRECT, natural {language} — the kind a native
> editor would pass. The level limits which structures you may USE, never
> correctness. If the content wants a structure outside the cage (past
> events at A1), recast the sentence so an allowed structure fits
> naturally — or use the needed structure anyway: one correct sentence
> slightly above level beats a broken sentence at level, because glosses
> and translations are one tap away. Never bend agreement, tense, or word
> order to seem simpler.

### 2. The substance rule (prompt, all modes)

> The learner is an adult; the level constrains the language, not the
> content. Every sentence should carry real information — a fact, a name,
> a number, a date, a place, a cause, a comparison. No filler ("X is
> amazing", "Do you know X?"), no padding. A good A1 text reads like a
> well-written encyclopedia entry for beginners, not a picture book.

### 3. The checker grows teeth to match

`emit_check` gains two required verdicts:

- `grammar_ok` — false on ANY grammatical error in the target language;
  simplified-but-broken is an automatic fail.
- `substance_ok` — false when sentences carry no information (filler,
  empty questions, restated title).

Both feed the existing one-retry-with-verdict loop and ship in
`reading["check"]`, so obedience stays observable. Failure of either is
a flunk exactly like `level_ok`.

### 4. The absolute level dial (A1–C2)

`complexity` accepts `easier|level|stretch|A1|A2|B1|B2|C1|C2`.

- An explicit CEFR value pins `target_level` to exactly that level —
  the learner's resolved level no longer moves it.
- Cage choice by comparison: explicit level ABOVE the learner's resolved
  level → the open (stretch-style) constraints, because they asked for
  harder and glosses absorb the cost; at or below → the closed cage
  pitched at the chosen level.
- Frontend: the Challenge row gains A1–C2 chips after
  Easier / My level / Stretch. CEFR codes are level names in every
  locale — no new translation keys needed beyond the row itself.

## Testing

- Prompt tests: correctness invariant + substance rule present in BOTH
  cages (closed and stretch); regression phrasing pinned ("never bend
  agreement", "encyclopedia entry").
- Dial matrix: explicit levels pin the target regardless of learner
  level; open vs closed cage chosen by comparison; relative modes
  unchanged.
- Checker: schema requires grammar_ok + substance_ok; a verdict with
  either false triggers the retry.
- Router: pattern accepts the nine values, rejects garbage.
- Frontend: option row renders nine choices; picking B2 sends
  complexity: 'B2'.

## Non-goals

- No second full-model proofread pass — the graded-retry loop already
  bounds cost at one regeneration, and the grader is the cheap model.
- No change to the "no translations on first pass" pedagogy.
- Seeded/stored past readings are not regraded; the fix is forward.
