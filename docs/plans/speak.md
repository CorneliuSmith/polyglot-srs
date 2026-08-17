# Speak — conversation practice with a correction pass

A feature plan. **All four stages are built, plus a fifth (the
conversation options) added on the owner's request.** Stage 2 shipped on Azure's
fast-transcription tier, on the same key and region the app already used
for neural TTS — the recommendation from docs/plans/speak-speech.md, taken
as written.

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
| 2 ✅ | Speech in and out | Latency work lands against something already known to work |
| 3 ✅ | Coach mode | The interrupting correction is the riskiest UX call; earn the right to it |
| 4 ✅ | Cards from the summary | Wire to personal cards once the errors are known to be worth keeping |
| 5 ✅ | Conversation options (auto-speak, hidden text, auto-listen, auto-send) | Added after use: the manual replay button was the only way to hear anything |

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

### What stage 2 shipped

`services/stt.py` (Azure fast transcription), `POST /api/speak/transcribe`,
`POST /api/speak/say`, `features/speak/useRecorder.ts`, and a `speech`
block on `/api/speak/status`. No new vendor and no new secret: STT is a
different endpoint on the Speech resource already in production.

**The recording is never kept.** It is read into memory, transcribed, and
dropped when the request returns — not written to storage, not logged, not
retained to save a re-record. The response carries the transcript and no
handle by which the audio could be fetched again, because there isn't one.
A recording of someone's voice is biometric data; a language app has no
business holding it. The consent line says this in the interface, because
a microphone permission prompt is not consent.

**The transcript goes into the text box, not into a turn.** It is the same
box a typed turn is written in, and it is editable there. ASR mishears an
accented beginner, and being corrected for a word you did not say is the
fastest way to stop trusting the feature — so nothing is sent until the
learner has read it. It also leaves exactly one Send to reason about.

**Tap to start, tap to stop — not hold-to-talk.** The plan sketched
push-to-talk and it is the better metaphor right up until you build it: a
`pointerup` that lands outside the button never fires, so the recorder runs
on with the microphone light lit. It is also unreachable by keyboard, which
would make the one place in the app that practises production the one place
a keyboard user cannot go.

**Listening and speaking are separate facts and neither implies the
other.** `/status` reports both. Speak can hear Hebrew, Persian, Indonesian
and Filipino, none of which have a neural voice; it cannot hear Latin,
Māori, Xhosa, Yoruba, Hausa or Jamaican Patois, and Māori and Latin do have
voices in the reader. A course missing either half keeps the typed path
permanently — the start screen says so on the way in, rather than the
learner discovering a missing button mid-conversation.

**"Say that again" replays the same line slower** (-35% against the usual
-10%), fetched on press rather than with the turn: most lines are never
replayed and synthesizing all of them up front would spend real money on
audio nobody listens to. This was the control the plan argued hardest for
— comprehension failure is the commonest reason a conversation dies.

Two things worth knowing for whoever touches this next:

- **The partner's line is synthesized through Speak, not `/api/audio/tts`.**
  That endpoint checks the text is one of *ours* — a drill sentence, an
  example, a vocabulary word — which is what keeps it from being an open
  synthesis proxy. A reply written seconds ago for one learner passes no
  such test, so the check here is ownership instead: the line is read back
  out of the caller's own session and nothing the client sends is
  synthesized.
- **Format is the whole cross-browser story.** Chrome and Firefox record
  WebM/Opus; Safari has no WebM encoder and produces MP4/AAC. The
  recorder probes with `isTypeSupported` and falls back to the browser
  default rather than throwing, and the server matches MIME types on their
  base so `audio/webm;codecs=opus` is recognised as WebM.

### What stage 3 shipped

The mode chooser the mockup above promised, and it does what the mockup
says: in Coach mode a turn comes back with exactly ONE correction, never a
list. The model is asked to order its findings most-impeding-first and the
first is the one shown; the rest are stored and reach the summary like
everything else, so nothing is lost by not interrupting with it.

Flow sends no `correction` key at all — not an empty one. A client cannot
render what it was never given, so the promise does not depend on the
frontend behaving. Coach sends the key even when the turn was clean (as
`null`), so "nothing was wrong" is distinguishable from "this mode does not
correct".

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

### What stage 5 shipped — the conversation options

The owner: *"For speaking the audio never auto-speaks for users. Instead,
they have to click the repeat slowly. Create options that provides users real
convo situations. Audio output automatic or not. Audio response hidden or
not, auto-response wait (I don't know the best way to do this feature but
listen for the audio input immediately and send for them when they stop for a
bit)."*

Four switches, in `prefsStore.speakConversation`, all defaulting OFF so a
session behaves exactly as it did until somebody asks for more:

| Switch | What it does | Needs |
| --- | --- | --- |
| Speak out loud | plays each partner line as it arrives | a voice for the course |
| Hide the words | the line is heard, not read, with a one-tap reveal | a voice for the course |
| Listen automatically | opens the microphone when the partner finishes | a recognizer + MediaRecorder |
| Send when I stop talking | ends and sends the turn on a pause | the above + an AudioContext |

Plus one button that turns the last three on together, for the people who
just want hands-free.

**They are four switches rather than one mode** because they fail
differently. Someone on a train wants the partner's text without its voice;
someone practising listening wants the voice without the text; someone in a
quiet office wants neither but still wants the microphone armed. A single
"hands-free mode" would have to pick one of those for everybody.

Five decisions worth knowing:

- **The microphone opens only when the clip has ENDED.** `playLine` resolves
  on the audio element's `ended` event and only then arms the recorder.
  Arming it any earlier records the partner's own voice back into the
  learner's transcript, which is the obvious bug in this feature and the one
  a test pins.
- **Auto-send did not delete the transcript-review decision from stage 2 — it
  turned it into a grace window.** The transcript still appears, for
  `AUTO_SEND_GRACE_MS` (2s), with a Cancel that moves it into the text box
  for editing. Hands-free means nobody has to press anything; it does not
  mean being corrected for words you never said.
- **Silence detection is adaptive, and reports WHY it stopped**
  (`features/speak/silence.ts`). The gate sits a few times above the
  quietest level seen so far, clamped at both ends: a fixed threshold makes
  soft speakers inaudible in a study and everybody inaudible in a café, and
  without the ceiling a learner who starts talking before the first sample
  would set the floor from their own voice. `silence` and `max` transcribe;
  **`nothing` throws the recording away without calling the provider**,
  because an empty transcription costs money and buys nothing.
- **A switch whose prerequisite is missing is shown DISABLED with the
  reason**, never hidden and never quietly inert. `canDetectSilence()` gates
  auto-send, `speech.speak` gates the two audio switches, `recordingSupported()`
  gates the microphone ones.
- **Auto-speak shares one audio element and one clip cache with the replay
  buttons.** The element is primed with a silent clip inside the Start tap,
  because mobile Safari only plays a media element programmatically after it
  has played once inside a real gesture; if playback is refused anyway the
  page says so and the manual buttons still work. The cache means hearing a
  line again — the "say that again, slower" that started this whole
  request — costs nothing the second time.

**Cost note.** Auto-speak synthesizes every line rather than the ones a
learner asks for, so a 20-turn conversation goes from a handful of clips to
20. At Azure's $16/1M characters that is about 5¢ per hundred conversations —
irrelevant next to the model call. Continuous listening is the one to watch
if batch STT ever moves to the real-time tier.

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
   of v1 and say so in the UI rather than do it badly. **Stage 2 shipped
   without it** — and because the audio is discarded, adding it later means
   deciding to keep recordings for the length of one scoring call, which is
   a privacy decision rather than a feature decision.

5. **Is 2–3 seconds acceptable?** Batch transcription was chosen over
   streaming at a fifth of the price (docs/plans/speak-speech.md). If the
   pause after releasing reads as broken in real use, the move is Azure's
   real-time tier — same vendor, same key, a websocket, and about
   $0.042/session instead of $0.008.
