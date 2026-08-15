# Speak — conversation practice with a correction pass

A feature plan. **Stages 1 and 4 are built** (typed Flow mode, the
end-of-session summary, and opt-in cards from it — see the sequencing table
below). Stages 2 and 3 are still design to argue with before anyone writes
code.

Stage 4 came before 2 and 3 deliberately: speech needs an STT provider this
codebase does not have and the owner has not chosen, whereas cards need
nothing new and are what makes a Speak session feed the rest of the app.

**Name: Speak.** It sits in Practice alongside Gym and Read. Those two are
recognition and comprehension; this is the only place the learner *produces*
language under time pressure, which is the skill they will actually be judged
on and the one the app currently never asks for.

---

## What the learner does

Open Practice → **Speak** → choose a mode → talk.

```
┌───────────────────────────────────────────┐
│  Speak            Spanish · B1            │
│                                           │
│   ○ Coach     corrections as you go       │
│   ● Flow      corrections at the end      │
│                                           │
│   Topic  [ Ordering at a café        ▾ ]  │
│          [ Anything — you start      ▾ ]  │
│                                           │
│            ( Start talking )              │
└───────────────────────────────────────────┘
```

Then a turn loop: they hold to speak (or tap to toggle), it transcribes, the
partner replies out loud and in text, and they go again. A single **Done**
button ends it whenever they like — the session is never "over" because a
counter ran out.

### Coach mode

After each of the learner's turns, before the reply:

```
   You said                                    0:12
   "Yo quiero un café con leche, por favor"
   ┌─────────────────────────────────────────┐
   │ ✓ Natural. One nudge:                   │
   │   "Yo quiero" → "Quiero"                │
   │   Spanish drops the subject pronoun     │
   │   unless you're contrasting.            │
   └─────────────────────────────────────────┘

   Partner  "Claro. ¿Para tomar aquí o para llevar?"   🔊
```

The correction is **one line, one point, then the conversation moves on.**
Never a list. If there are three errors, take the one that most impedes being
understood and let the others accumulate for the summary. A learner corrected
three times per turn stops talking.

### Flow mode

Identical, minus the correction card. Errors are recorded silently and all
land in the summary. This is the mode for fluency and for nerves.

**Both modes end with the same summary** — Flow is not "no feedback", it is
"feedback that does not interrupt".

### The summary

```
   8 turns · 4 min · you spoke 61% of the time

   What came up
   ┌─────────────────────────────────────────┐
   │ Subject pronouns          3 times       │
   │ You said "yo quiero", "yo creo",        │
   │ "yo pienso". Spanish drops these        │
   │ unless contrasting.        [ + Add ]    │
   ├─────────────────────────────────────────┤
   │ ser vs estar              2 times       │
   │ "soy cansado" → "estoy cansado"         │
   │                            [ + Add ]    │
   └─────────────────────────────────────────┘

   Words you reached for
   café con leche · para llevar · la cuenta     [ + Add all ]

   ( Practise these )        ( Talk again )
```

Two kinds of card offered, both **opt-in, nothing auto-added**:

- **Grammar**: a personal card built from *their own sentence*, corrected.
  The prompt is what they meant; the answer is what they should have said.
- **Vocabulary**: words the partner used that they visibly did not have, and
  words they asked for mid-sentence.

"Practise these" adds the accepted cards and drops straight into a session.

---

## What I would add that was not asked for

Five things, in the order I would fight for them:

1. **A "say that again" button on the partner's turn.** Replays slower.
   Comprehension failure is the commonest reason a conversation dies, and
   without this the learner's only recovery is to quit.

2. **Let them type instead.** Some people cannot speak out loud — open-plan
   office, sleeping baby, self-consciousness. A text fallback costs one input
   and roughly doubles the situations the feature is usable in.

3. **Show the transcript as it lands, and let them fix it.** ASR will
   mishear an accented beginner, and being corrected for a word you did not
   say is the fastest way to lose trust in the feature. A tap-to-edit
   transcript also tells you your ASR accuracy for free.

4. **Cap the partner's level.** It should speak at roughly the learner's
   level plus a little, not like a native at full speed. Without an explicit
   instruction the model writes B2 prose at an A2 learner and the session
   becomes a listening test they fail.

5. **Let them end mid-turn without losing the summary.** People get
   interrupted. The summary should be computed from whatever happened.

And one thing to deliberately *not* build: a score. The moment there is a
number, Flow mode becomes a thing to game and the learner stops experimenting.
Count turns and time, not quality.

---

## How it hangs together

```
  ┌────────┐  audio   ┌─────────┐ text  ┌──────────────┐
  │ client │─────────►│   STT   │──────►│  turn engine │
  │        │◄─────────│   TTS   │◄──────│  (one call)  │
  └────────┘  audio   └─────────┘ text  └──────┬───────┘
       ▲                                        │
       │ transcript + correction + reply        │ per turn:
       └────────────────────────────────────────┘ reply + errors
                                                  (structured)
```

**One model call per turn**, returning both the conversational reply and the
structured error list. Two calls doubles latency and the reply is better when
the model has already noticed the mistake. Errors accumulate server-side; the
summary is assembled from them at the end with a second call only if the
grouping needs judgement.

**Latency is the whole product.** Target under 1.5s from end-of-speech to
first audio. Above ~3s it stops feeling like conversation and becomes
turn-taking with a form. That budget is the main constraint on every other
decision here — it is why the correction is one line, and why reply and
analysis share a call.

Schema sketch, minimal:

```
speak_sessions   id, user_id, language_id, mode, topic,
                 started_at, ended_at, turn_count
speak_turns      session_id, idx, learner_text, partner_text,
                 audio_ms, errors jsonb
```

`errors` as JSONB rather than its own table: it is written once, read once,
and never queried across sessions until there is a reason to.

Reuses what exists: TTS (`services/tts.py`, already per-language voiced),
the allowance meter, personal cards (`card_type='personal'` — the summary
adds through the same path as `TranslateMyCards`), and the learner-level
context already assembled for Tutor.

---

## Sequencing

Each stage is usable on its own; stop after any of them.

| Stage | What ships | Why this order |
| --- | --- | --- |
| 1 ✅ | Text-only Flow mode + summary | Proves the turn engine and the error extraction with no audio risk at all |
| 2 | Speech in and out | Latency work lands against something already known to work |
| 3 | Coach mode | The interrupting correction is the riskiest UX call; earn the right to it |
| 4 ✅ | Cards from the summary | Wire to personal cards once the errors are known to be worth keeping |

Stage 1 is genuinely useful alone — a typed conversation partner with an
end-of-session breakdown is a real feature.

### What stage 1 actually shipped

`services/speak.py` (one tool call per turn returning reply + errors; a
second, cheaper call groups them at the end), `repositories/speak.py`,
`routers/speak.py` (`/status`, `/start`, `/turn`, `/end`),
`features/speak/SpeakPage.tsx`, and migration
`20260923000000_speak_sessions.sql`.

Four decisions worth knowing before building stage 2:

- **The turn response never carries the errors.** They are stored and
  withheld until `/end`. A client cannot leak what it is never sent, so
  flow mode's promise does not depend on the frontend behaving.
- **`/end` is not gated on the allowance.** Someone who spent their last
  message on the conversation still gets told what they got wrong. A
  session with no errors makes no model call at all.
- **The breakdown survives a failed summary call** — `_fallback_groups`
  groups mechanically by error type. Cruder, but a learner who finished a
  session always gets something.
- **The session, not the request, decides the course.** `/turn` takes only
  a session id; a client that passed its own `language_id` could aim a
  session at another course's model and level.

One thing the plan asked for that stage 1 does NOT do: there is no
`/status` entry until the migration is applied — the page reports itself
unavailable rather than offering a conversation that cannot be saved.

### What stage 4 shipped

The summary's cards are real. Each group carries a `card` built from the
learner's OWN corrected sentence, and each vocabulary item carries the
sentence from the conversation it appeared in, so both are practised in
context rather than as bare pairs. They file into a "From speaking" deck
through the same `/api/notes/cards` path `TranslateMyCards` uses.

Three things worth knowing:

- **Nothing is ever added automatically.** Every card is one deliberate
  tap. A summary that quietly filled someone's reviews would make them
  wary of finishing a session, which is the opposite of the point.
- **A card that could not be saved is never offered.** `_usable_card`
  checks the answer really appears in the sentence — the same rule the card
  endpoint enforces — so the Add button is absent rather than broken.
  Fallback groups carry no card at all: a per-turn error records the phrase
  that was wrong, not the sentence around it.
- **"Practise these" appears only once something has been kept**, and
  routes to the normal review session. There is no separate Speak-only
  drill mode to maintain.

---

## Open questions, for the owner

1. **What ends a session?** I have assumed a Done button and no turn limit.
   A soft nudge at ~10 turns ("good place to stop?") may serve people who
   would otherwise never stop, but it can also cut someone off mid-flow.

2. **Does Speak draw on the allowance meter?** It is the most expensive
   feature per minute in the app — STT + a model call + TTS per turn. It
   probably needs its own budget line and a visible meter, like Tutor.

3. **Is the partner a character or a narrator?** A named persona with a
   consistent voice is warmer and much easier to write prompts for; a
   neutral one is safer across cultures.

4. **Does Coach correct pronunciation?** Everything above is grammar and word
   choice from the transcript. Pronunciation needs the audio and a different
   kind of model, and is a much harder promise to keep. I would leave it out
   of v1 and say so in the UI rather than do it badly.
