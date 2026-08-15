# Speak stage 2 — what speech needs, and what it costs

Stage 2 of `docs/plans/speak.md` is "speech in and out". This is the
resourcing decision behind it: what has to be bought, what already exists,
and what a month of real use actually costs.

Prices checked 15 August 2026. They move — re-check before committing.

---

## The headline

**You already own the resource.** `backend/config.py` carries
`azure_speech_key` / `azure_speech_region`, used today for neural TTS. Azure
Speech does **speech-to-text on the same key, same resource, same region**.
There is no new vendor, no new contract, and no new secret to rotate — STT
is a different endpoint on infrastructure that is already in production.

**Audio is not the expensive part.** At the volumes below, the model turns
cost more than the microphone. Audio adds somewhere between 40% and 100% on
top of a session's existing cost, depending on which speech-to-text tier is
chosen — and the cheapest option is within a rounding error of the most
expensive one at beta scale.

**The free tier covers a beta outright.** Azure's F0 tier gives 5 STT audio
hours and 500,000 TTS characters per month, and does not expire. That is
about 120 spoken sessions a month at zero marginal cost.

---

## What one session costs

Modelled on the plan's own sketch: 8 turns, about 4 minutes wall clock, the
learner speaking roughly 61% of it (≈2.5 minutes of audio), the partner
replying with about 1,000 characters of synthesised speech.

### Speech-to-text — 2.5 minutes of learner audio

| Option | Rate | Per session | Notes |
| --- | --- | --- | --- |
| **Azure fast/batch** | $0.18 / audio hr | **$0.008** | Same key you already have |
| **Azure real-time** | $1.00 / audio hr | **$0.042** | Streaming; lowest latency |
| OpenAI `gpt-4o-mini-transcribe` | $0.003 / min | $0.008 | New vendor |
| OpenAI `gpt-4o-transcribe` | $0.006 / min | $0.015 | 4.1% WER vs Whisper's 5.3% |
| Deepgram Nova-3 batch | $0.0043 / min | $0.011 | New vendor |
| Deepgram Nova-3 streaming | $0.0077 / min | $0.019 | New vendor |
| AssemblyAI batch | $0.0025 / min | $0.006 | Cheapest per minute |

### Text-to-speech — ~1,000 characters of partner reply

| Option | Rate | Per session |
| --- | --- | --- |
| **Azure neural** (in production today) | $16 / 1M chars | **$0.016** |
| Azure Neural HD | $22 / 1M chars | $0.022 |

### The model turns, for scale

Eight turns with a growing history is roughly 12,000 input and 1,600 output
tokens per session — on the order of **$0.06** at Sonnet-class rates. This
is already being spent by stage 1 and already metered by the allowance.

### Totals

| Configuration | Audio | Model | Session total |
| --- | --- | --- | --- |
| Azure batch STT + Azure TTS | $0.024 | $0.06 | **$0.084** |
| Azure real-time STT + Azure TTS | $0.058 | $0.06 | **$0.118** |

---

## What a month costs

| Scale | Sessions/mo | Audio only | With model turns |
| --- | --- | --- | --- |
| Beta — 50 learners, 3×/week | ~650 | $16 – $38 | $55 – $77 |
| Growing — 200 learners, 3×/week | ~2,600 | $62 – $151 | $218 – $307 |
| 1,000 learners, 3×/week | ~13,000 | $312 – $754 | $1,090 – $1,534 |

The free tier absorbs the first ~120 sessions of STT and ~500 sessions of
TTS every month, so the beta row is closer to zero than it looks.

Azure commitment tiers cut STT to $0.50/hr at 50,000 hours a month and TTS
by up to 53% above 80M characters — both far beyond any scale on this table.
Ignore them until they matter.

---

## What has to be built or bought

Money is the easy part. These are the real prerequisites:

1. **Enable STT on the existing Azure resource.** No purchase; confirm the
   region (`eastus` today) serves STT for the courses that need it.

2. **Verify language coverage.** Azure STT covers many more languages than
   its TTS voice list, but the app has 17+ courses and several — Jamaican
   Patois, Māori, Xhosa, Yoruba, Latin — almost certainly have no STT model
   at all. Those courses need the typed fallback permanently, not as a
   stopgap. This must be checked per course before anything ships, the same
   way `VOICES` in `services/tts.py` was.

3. **Browser capture.** `getUserMedia` + `MediaRecorder`. HTTPS is already
   in place. The trap is format: Safari records `audio/mp4`, Chrome and
   Firefox `audio/webm` — the upload path has to accept both and tell Azure
   which it got. iOS also needs the recording started inside a user gesture.

4. **An upload endpoint that never keeps the audio.** Transcribe, return
   text, discard. Storing learner voice recordings turns a language app into
   a biometric data processor, with everything that implies.

5. **Consent, stated plainly.** A microphone permission prompt is not
   consent. One line before the first recording saying what happens to the
   audio and that it is not kept.

6. **A latency decision.** Batch upload of a finished utterance is simpler
   and lands at roughly 2–3 seconds end to end. The plan's 1.5s target needs
   streaming STT, which is Azure's $1/hr real-time tier and a websocket.
   **Recommendation: ship batch first** with push-to-talk (hold to speak,
   release to send). It is honest about when it is listening, it costs a
   fifth as much, and 2–3s is acceptable for a turn the learner deliberately
   ended. Move to streaming only if the pause actually reads as broken.

---

## Recommendation

Use **Azure batch STT plus the existing Azure TTS**. It adds no vendor, uses
a key already in production, costs about $0.024 a session, and is free for
the first ~120 sessions each month. Nothing in the comparison table beats it
by enough to justify onboarding a second speech provider — AssemblyAI's
$0.006 saves two tenths of a cent per session.

Revisit only if the push-to-talk pause proves unacceptable in testing, at
which point the choice is Azure real-time (same vendor, $0.042/session) or
Deepgram streaming (new vendor, $0.019/session).

---

## Sources

- Azure AI Speech pricing — STT $1/hr real-time, $0.18/hr batch; TTS $16/1M
  neural, $22/1M HD; F0 free tier 5 STT hours + 500K TTS chars per month.
- OpenAI transcription pricing — `gpt-4o-transcribe` $0.006/min,
  `gpt-4o-mini-transcribe` $0.003/min.
- Deepgram Nova-3 — $0.0043/min batch, $0.0077/min streaming.
- AssemblyAI — $0.0025/min batch.
