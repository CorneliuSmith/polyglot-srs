# Adaptive sessions: one level, obeyed dials, a feedback loop, and sessions that persist

A plan, not an implementation. The owner's report, condensed to its four
claims — each verified against the code before anything below was written:

1. Tutor/Read (and soon Speak) pitch content off the wrong level, and a
   level changed by the user is not taken into account.
2. Read does not actually obey the rules the user sets, and its content is
   sometimes far too simple.
3. There should be retrieval-backed ("RAG") depth for users who want more
   substantive content, across Tutor, Speak and Read.
4. Sessions should be endable and revisitable, and account state generally
   must be adhered to across the board — even if that means rewriting
   pieces properly rather than patching.

All four are real. The first two share one root cause, and it is the same
disease the support-locale freeze had: **more than one place claims to be
the truth, and the one the user can touch is not the one the features
read.**

---

## Findings, with the receipts

### F1 — There are THREE level systems, and the user controls the wrong one

| Level notion | Where it lives | Who reads it |
| --- | --- | --- |
| **Deck level** — highest subscribed deck | derived from `user_content_subscriptions`; `set_learner_level` (repositories/onboarding.py:728) re-seats it | Settings *displays* it; Learn draws from it |
| **Card level** — "highest CEFR level with a meaningful number of started items, fallback A1" | computed per request in `get_learner_model` (repositories/reader.py:12) | **every AI prompt**: Tutor (depth="full"), Reader, Speak all take `learner["level"]` from `get_assessment_summary` (repositories/assessment.py:99) |
| **Placement level** | `get_placement_insight` | only *primes* the card level, and only during cold start (< `_BASELINE_CARD_CUTOFF` cards, assessment.py:123-149) |

**When the user changes their level in Settings, nothing is stored.** The
SettingsPage comment says it outright: *"there's no separate stored level"*
(SettingsPage.tsx:282-284). `set_learner_level` re-seats deck
subscriptions and returns — the AI features never hear about it, because
they read the card-derived level, which only ever moves as slowly as the
card history does. A B2 speaker who joined last month has A1/A2 cards, so
the Tutor talks to them like a beginner *no matter what they set*, and the
cold-start placement priming stops applying the moment they have enough
cards — which, perversely, means studying MORE makes the mispitch
*stickier*.

This is the locale bug's shape exactly: the lever the user can reach
(Settings) is disconnected from the value the features consume.

### F2 — Reader's dials are whispers against a cage

The reader prompt (services/reader.py:135-160) ends in:

```
HARD CONSTRAINTS:
- Grammar: use ONLY structures the learner has learned: {…}
- Vocabulary: stay within what a {level} learner knows. Their strongest
  known words, for calibration: {40 stability-ranked words}
```

while the user's `complexity: "stretch"` contributes one soft sentence
("slightly more complex… a subordinate clause here and there"). A hard
constraint plus a soft nudge resolves, in a language model, to the hard
constraint. With F1 pinning `{level}` at A1-because-cards, and "structures
the learner has learned" listing whatever few grammar cards exist, the
model is *caged* into baby text — and the stretch dial cannot open the
cage because it never changes the level or the constraint set, only tone.

`length` and `voice` are structurally fine (services/reader.py:82-95) but
nothing ever *verifies* the output honored any dial. The user says it
doesn't always; there is currently no way to know how often.

### F3 — The features observe skill and throw the evidence away

The evidence the user says should drive adaptation already exists, stored,
per feature — and none of it flows back:

| Signal | Where it sits | Feeds the learner model? |
| --- | --- | --- |
| Speak per-turn error list | `speak_turns.errors` JSONB | **No** |
| Speak session summaries (grouped error types) | `speak_sessions.summary` | **No** |
| Tutor session summaries + memory profile | `tutor_sessions`, `tutor_language_profile` | **No** (memory feeds the tutor's own prompt only) |
| Reader comprehension gaps | `grammar_gap_log` (reader migration) | **No** |
| Review accuracy, gym per-cell struggles, placement, writing sample | assessment.py | Yes — this is ALL it reads |

So "adjust based on what users show" currently means "adjust based on
flashcard grades" — the narrowest signal, and the one least like real
production. Someone who converses fluently in Speak but reviews casually
reads as weak.

### F4 — Session lifecycle is inconsistent across the three features

| | End explicitly | Summary | Revisit past sessions | Resume open session |
| --- | --- | --- | --- | --- |
| Tutor | yes | yes (stored) | **yes** — Past sessions UI (TutorPage.tsx:326) | rolling memory, no per-session resume |
| Read | n/a (texts, not turns) | n/a | **yes** — `GET /readings` library | yes (texts persist) |
| Speak | yes (Done) | yes (stored) | **NO** — `list_recent_sessions` is returned by `/status` but SpeakPage never renders it, and no endpoint serves a past session's transcript or summary | **NO** — an unfinished session is stranded (turns are in the DB; the UI can't reattach) |

Speak stores the most complete record of the three (full transcripts) and
exposes the least of it.

### F5 — Account-state conformance is a bug *class*, not a bug

Incidents to date, all the same shape (stored preference ≠ consumed value):
the support-locale freeze (#277/#278), the tutor model that kept resetting
(task #77), admin settings not persisting (#75), Kate's level with no way
out (#64), and now F1. Each was found by a user hitting it. There is no
test layer whose job is "every stored preference reaches every consumer."

---

## The design

### One rule for level, mirroring the locale rule that just shipped

```
explicit choice  →  chosen_level     (set in Settings / after placement;
                                      a FLOOR the features must respect)
evidence         →  demonstrated     (cards + placement + speak errors +
                                      tutor corrections + reader gaps;
                                      may pitch ABOVE the floor, never
                                      silently below it)
effective_level  =  max(chosen_level, demonstrated)   — resolved at READ
                    time, one module, every consumer
```

Demotion is never silent: if the evidence says the chosen level is too
high, the features stay at the floor and the app *tells* the user
("Reviews suggest B1 is a stretch right now — keep B2 anyway / drop to
B1"), the same consent posture as everything else in this app. The user's
statement of their own ability is respected the way their language choice
now is; the machine argues, it does not overrule.

One module — `backend/repositories/level.py`, the twin of
`repositories/profile.py` — exposes `effective_level(conn, user_id,
language_id)` and is the ONLY thing any prompt-building surface may call.
`get_assessment_summary` keeps its role (weak areas, focus, placement
detail) but its `level` field is computed by this module.

### Dials become contracts, and contracts get checked

The anti-trash mechanism, and the most important paragraph in this plan:
**generated content gets graded before it is served.** A cheap checker
pass (same model family, one small call) receives the text plus the
contract — level, length band, voice, complexity — and returns pass/fail
per dial. One regeneration on failure with the verdict injected; serve the
second attempt either way and LOG the verdict. That log is the honest
answer to "does Read actually listen": a per-dial obedience rate on the
admin panel instead of anecdote. The maker–checker pattern already runs
the content pipeline; this applies it to learner-facing generation.

`complexity` stops being tone and becomes a **level shift**: `easier` =
effective−1 as the cage, `level` = effective, `stretch` = effective+1 with
known-vocabulary reframed from cage to calibration ("their strongest words
for reference — do not limit yourself to them"). The HARD CONSTRAINTS
block is rewritten per mode; stretch explicitly licenses unknown
vocabulary since glosses are one tap away — that is what the Reader's
gloss machinery is *for*.

### The feedback loop (demonstrated skill)

A nightly-or-on-session-end aggregation, not per-request scoring:

- **Speak**: error-per-turn rate and error types from `speak_turns.errors`
  — the richest production signal in the app, currently discarded.
- **Tutor**: correction density from session summaries.
- **Read**: `grammar_gap_log` density + per-text lookup rate.
- **Cards/Gym/Placement**: what assessment.py already reads.

Rolled into a `demonstrated` CEFR estimate with a confidence, stored per
(user, language), surfaced in Settings next to the chosen level ("You set
B1 · recent sessions look like B2 — raise?"). Promotion nudges, never
silent moves, either direction.

### RAG — for substance, not difficulty

Honest scoping: stages 1–2 fix "too simple". Retrieval is for
**substantive** — content grounded in real material instead of the
model's generic register. Design:

- **Store**: pgvector (a Supabase-native extension — one migration).
- **Corpus, internal first**: reviewed example sentences, grammar
  explanations + culture/function notes, the About/trivia fact corpora,
  the learner's own past readings and speak/tutor summaries. All of it
  already exists and is already reviewed content.
- **Retrieval points**: Read "substantive" mode (retrieve facts + related
  reviewed sentences on the topic → ground the text); Tutor and Speak
  (retrieve the learner's relevant past-session summaries + weak-area
  explanations → the partner remembers and targets, beyond the rolling
  memory's recency horizon).
- **Embeddings decision (owner)**: a hosted embeddings API (Voyage is the
  natural pairing; pennies at this scale) vs. a small self-hosted
  multilingual model in the backend container (~100 MB RAM, no vendor).
  Recommendation: hosted, behind the same one-function seam as TTS, so
  swapping later changes nothing upstream.

### Sessions

- **Speak**: render the `sessions` list `/status` already returns; add
  `GET /api/speak/sessions/{id}` (transcript + summary, owner-scoped like
  every other speak endpoint); a session with no `ended_at` gets a
  "Continue" that reattaches (turns are already in the DB — this is pure
  UI plus one read endpoint). End stays one tap.
- **Tutor**: past sessions exist; decide whether to store transcripts
  (today: summaries only — a deliberate privacy posture; owner call, not
  assumed).
- **Read**: the library exists; gets the same session-row treatment on the
  page for consistency.

### The conformance layer (the "across the board" ask)

A matrix test suite, `backend/tests/test_state_conformance.py`,
parametrized over **every stored preference × every consumer**: level,
support locale, ui language, batch size, explicit-content filter,
accents-optional, tashkeel, qwerty-translit, tutor model override, session
size, reminder settings. Each cell asserts the stored value demonstrably
reaches the consumer's behavior (prompt content, query filter, or response
field). New preferences fail CI until they join the matrix. This converts
the recurring bug class — five incidents so far — into a test failure
instead of a user report. Frontend twin: settings changes invalidate the
right queries (the epoch pattern ReviewSessionPage/LearnPage already use,
generalized).

---

## Sequencing — PR-sized, in dependency order

| PR | Ships | Proves itself by |
| --- | --- | --- |
| 1 | `learner_levels` migration (chosen_level, demonstrated, confidence, source, updated_at) + `repositories/level.py` + Settings writes chosen_level (keeps re-seating decks) + all prompt surfaces read `effective_level` | Matrix tests: set level in Settings → Tutor/Read/Speak prompts carry it, immediately; degrade-without-migration test (CLAUDE.md rule) |
| 2 | Reader dial rewrite (complexity = level shift, cage → calibration for stretch) + the checker pass + verdict log | Grader-verified: 20 generated texts across dials, per-dial obedience asserted in an integration test; verdicts visible in admin |
| 3 | Demonstrated-skill aggregation (speak errors, tutor corrections, reader gaps → `demonstrated`) + Settings nudge UI | Fixture sessions with planted error rates move `demonstrated` predictably; never moves `chosen_level` |
| 4 | Speak sessions: history UI, transcript/summary revisit, resume-unfinished | A stranded session is reattachable; past summaries browsable |
| 5 | Conformance matrix suite, full breadth + frontend invalidation audit | Every existing preference passes; a deliberately broken consumer fails |
| 6 | RAG: pgvector migration, embedding seam + corpus backfill CLI, Read "substantive" mode | Substantive text demonstrably quotes/grounds retrieved facts; A/B against non-RAG in the verdict log |
| 7 | RAG into Tutor + Speak (long-horizon memory retrieval) | Partner references a specific weeks-old session detail in a fixture |

Each PR is independently shippable; stopping after 2 already resolves the
reported symptoms. 6–7 are the substance layer and carry the two owner
decisions (embeddings provider; tutor transcript storage).

## Owner decisions needed before the relevant PR

1. **PR 1**: on a level *downgrade* in Settings, should decks above the new
   level unsubscribe (current `set_learner_level` behavior) — assumed yes.
2. **PR 3**: may `demonstrated` ever *lower* pitch below chosen_level with
   consent prompt, or is chosen_level an absolute floor? Assumed: absolute
   floor, nudge only.
3. **PR 6**: embeddings — hosted (recommended) or self-hosted; and enable
   pgvector on the Supabase project (owner action, like all migrations).
4. **PR 4/tutor**: store tutor transcripts, or keep summaries-only?

## What this deliberately does not do

- No auto-demotion, ever. The user's stated level is a floor, exactly as
  their language choice is now authoritative.
- No per-request model scoring of the learner (cost, latency); the loop
  aggregates stored evidence.
- No external web retrieval in RAG v1 — the internal corpus is reviewed,
  licensed, and already good; external sourcing is a separate decision.
- No score shown to the learner (the Speak plan's rule, kept): levels and
  nudges, not grades.
