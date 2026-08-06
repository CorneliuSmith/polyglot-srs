# Offline packs

A learner downloads a language pack on wifi, gets on a plane, studies for
three hours, lands, and their reviews sync. That is the whole goal.

This document is the design, not the implementation. Nothing described here
is built yet.

## Does this force native apps?

No — with one honest caveat.

The two genuinely hard parts of offline study are answer grading and
scheduling, and both are pure client-side computation. A Capacitor shell
runs the same JavaScript in a WebView; it does not help with either. The
Capacitor projects in `frontend/android` and `frontend/ios` already bundle
`webDir: 'dist'` (see [`native-apps.md`](native-apps.md)), so everything
built for the web arrives in the apps unchanged the day we want them.

The caveat is **storage durability**, and it is entirely about audio. See
[Storage and eviction](#storage-and-eviction) — the short version is that a
text-only pack is safe everywhere, and a pack with a language's worth of TTS
clips is where the native argument eventually becomes real.

Build it in the web layer. Web ships on deploy; the apps ship on a store
review cycle, and a sync layer is exactly the kind of thing that needs ten
iterations in its first month.

## What works offline today

The shell, and nothing else.

`frontend/public/sw.js` caches `/` (network-first, falling back to the
cached copy) and hashed `/assets/*` (cache-first, safe because they are
immutable by construction). Everything else — every API call, and all
cross-origin audio from the Supabase `tts` bucket — goes straight to the
network by explicit design, so a stale cache can never break a deploy.

There is no IndexedDB anywhere in `frontend/src`. An offline learner today
gets a loading skeleton.

## The four things that must move to the client

### 1. Grading

`POST /api/review/validate-answer` (`backend/routers/review.py:797`) hands
the typed answer to the per-language NLP backend. That grader is
morphology-aware and coaches on diacritics rather than failing them — it is
the single most distinctive thing in the product, and it is Python.

Offline it cannot run. The plan is a deliberately weaker client grader,
shipped inside the pack:

- Unicode NFC normalise, casefold, strip leading/trailing punctuation.
- Apply a per-language **fold table** carried in the pack — the diacritic
  and orthographic equivalences that language treats as near-misses (`é≈e`,
  `ı≈i`, Arabic short vowels when the learner has them switched off).
- Exact match after folding → `correct`. Match before folding but not after,
  or a Levenshtein distance of 1 → `close`. Otherwise `incorrect`.

This will disagree with the real grader. That is accepted, and handled by
re-grading on sync (below) rather than by pretending the client is right.

The fold tables are the one piece of genuinely new linguistic content this
project needs, and they should be derived from the existing NLP backends
rather than hand-written a second time.

### 2. Scheduling

`POST /api/review/submit` reads the card's FSRS state, resolves the
effective per-user-per-language fitted weights via `get_effective_params`,
computes the next interval and writes.

FSRS is deterministic: given `(state, rating, elapsed_days, params)` the
result is identical anywhere. So ship the resolved params in the pack,
port the same step to TypeScript, and let the client schedule locally.

The port must be exact, and the way to guarantee that is a **shared fixture
file**: a JSON list of `(input, expected_output)` cases generated from the
Python implementation, asserted by both the Python and the TypeScript test
suites. A drift between the two is otherwise invisible until a learner's
intervals quietly diverge.

### 3. The session token

This is the sleeper problem and it will bite first.

`frontend/src/api/client.ts:9` attaches a Supabase JWT to every request by
calling `supabase.auth.getSession()`. Access tokens are short-lived;
refreshing needs the network. Three hours into a flight there is no valid
token, and any code path that treats "no session" as "logged out" will throw
the learner back to a sign-in screen while sitting on a complete local pack.

So: **the local store must be readable without a live token.** Offline
identity comes from the user id recorded in the pack manifest at download
time, the outbox is written unauthenticated, and the token is only required
at sync. The route guards need an explicit "we have a pack for this user"
branch that does not consult Supabase.

### 4. Nothing else

Everything remaining is data, and all of it is already persisted
server-side and reachable by an authenticated GET.

## What is permanently online-only

Anything that costs a model call:

| Endpoint | Why |
|---|---|
| `POST /api/reader/generate` | Generates the text; allowance-gated |
| `POST /api/reader/readings/{id}/explain` | Per-sentence grammar; allowance-gated |
| `POST /api/review/gym/generate` | One allowance message per form topped up |
| Tutor, in all its forms | Live conversation |

Offline these serve only what was downloaded, which means each one needs a
real answer to "you have used up what you brought with you" — a stated
count before departure (*12 readings downloaded*) is worth far more than a
graceful error afterwards.

## The pack

### Shape

```
GET /api/packs/{language_id}/manifest
      → { version, generated_at, user_id, sections: [
            { name: "review", items: 1840, bytes: 612000, hash: "…" }, … ] }

GET /api/packs/{language_id}?sections=review,read,gym&since=<version>
      → NDJSON, one record per line
```

`since` makes a top-up cheap: a learner who downloaded last week fetches the
delta, not the language. The per-section hash lets the client verify a
partial download rather than storing half a pack and discovering it at
altitude.

### Contents by feature

**Review** — the learner's due and near-due cards: word, translation,
gloss, example sentence and its translation, the card's current FSRS state,
plus the resolved FSRS params and the language's fold table. Lookahead is a
setting; the default should be roughly 30 days of scheduled work, not
"everything", because the pack is for a trip.

**Grammar** — explanations, culture notes and drills for the points those
cards touch, in the learner's support locale. Whatever the auto-translate
loop has filled; untranslated fields fall back to English exactly as they do
online.

**Read** — the shelf (`GET /api/reader/readings`) and every reading body
(`GET /api/reader/readings/{id}`). These are already persisted per user
under RLS, so this is a straight cache. Explanations are not included:
they're generated per request.

**Gym** — the drill sets for the forms in the learner's current gym
manifest. Attempts are recorded by `POST /api/review/gym/attempt`, which is
explicitly ungraded and never touches the SRS schedule — a pure append. That
makes Gym by far the easiest thing to sync and a sensible first target.

**Letters & Sounds** and the language guides are static client data already
inside the JS bundle, so the service worker covers them for free today.

**Audio** — optional, and the whole storage question. Clips are MP3s in the
public `tts` bucket under a deterministic key,
`sha256(voice \0 text)[:40]` (`backend/services/tts.py:54`). Because the
bucket is public and the key is derivable, the pack only needs to carry the
key list; the client fetches blobs straight from the CDN with no auth. Four
languages (yo, ha, xh, mi) have no neural voice and already fall back to
browser synthesis, which is local anyway.

### Sizing

Estimates, with the arithmetic shown so they can be checked against real
data rather than believed:

| Section | Per item | 1 language | Notes |
|---|---|---|---|
| Cards | ~400 B | ~0.8 MB | 2,000 cards with sentence + translation |
| Grammar | ~3 KB | ~0.6 MB | ~200 points with notes and drills |
| Readings | ~4 KB | ~0.2 MB | ~50 readings |
| Gym sets | ~500 B | ~0.3 MB | |
| **Text total** | | **~2 MB** | |
| Word audio | ~12 KB | ~24 MB | 2,000 clips, ~2 s at 48 kbps |
| Sentence audio | ~30 KB | ~60 MB | 2,000 clips, ~5 s |
| **With audio** | | **~85 MB** | |

Two orders of magnitude between them. That gap is the entire design
tension: text is free and safe on every platform, audio is not.

The consequence for the UI: audio must be a **separate, explicit, per-pack
opt-in with the size shown before download**, never a silent part of "get
this language".

## Writes: the outbox

One IndexedDB object store, append-only, drained on reconnect.

```
outbox: { id, kind, payload, occurred_at, attempts, last_error, status }
```

`id` is a client-generated UUID, and it is the idempotency key. Replay must
be safe — a sync interrupted halfway through must be resumable without
double-applying anything.

### Per kind

| Kind | Conflict risk | Rule |
|---|---|---|
| `gym_attempt` | None | Append. Ungraded, no schedule effect. |
| `card_known` | Idempotent | Last write wins. |
| `card_feedback` | None | Append. |
| `review` | **Real** | See below. |

### Reviews

Two backend changes are required, and neither is optional:

1. **`/submit` must accept `reviewed_at`.** It currently stamps
   `now = datetime.now(UTC)` and derives `elapsed_days` from it. Replaying a
   three-hour-old flight's reviews at landing time would compute every
   interval from the wrong moment. Clamp the supplied value to
   `[last_review, server_now]` so a device with a wrong clock cannot poison
   a schedule.

2. **`review_logs` needs a unique `client_review_id`.** Without it, a
   retried sync re-applies FSRS to the same card twice. This is a migration,
   and per the project's working agreement migrations are applied by the
   owner — so the sync endpoint must probe for the column and refuse to
   accept queued reviews rather than accepting them unsafely when it is
   missing. Degrading here means "sync is unavailable, your work is still on
   the device", not "sync silently corrupts a schedule".

Reviews for one card replay **in `occurred_at` order**, because FSRS is
path-dependent. Across cards the order does not matter.

### Re-grading

The server re-runs the real NLP grader on every synced answer. Where it
disagrees with the client's verdict, the server's result is authoritative
and the card's schedule is recomputed from it.

Disagreements are counted and reported. A fold table that produces a
disagreement rate above a few percent is a bug in that table, and the only
way anyone will ever find out is if the number is visible — the same lesson
as the translation sweep heartbeat.

## Storage and eviction

| Platform | Durability |
|---|---|
| Desktop browser | Large quota, eviction only under real pressure. Fine. |
| Android Chrome (installed) | Same. `navigator.storage.persist()` is generally granted. Fine. |
| iOS Safari, plain tab | Bounded quota, and script-writable storage is cleared after 7 days without a visit. **Not safe for a pack.** |
| iOS, installed to home screen | Exempt from the 7-day clearance and given a more durable allowance. Safe in practice for text; audio depends on device pressure. |
| Native (Capacitor) | Filesystem. Not evicted. |

Two things follow. First, `InstallPrompt.tsx` stops being a nice-to-have on
iOS and becomes a **precondition** — a pack downloaded in a Safari tab can
evaporate before the trip. The download flow must say so and must refuse to
download a large pack in a non-installed iOS tab.

Second, this is the only place where native genuinely wins, and it wins in
proportion to audio. If audio packs turn out to be what people actually
want, that is the moment the app conversation becomes about capability
rather than distribution.

Call `navigator.storage.estimate()` before download and `persist()` after,
everywhere. Neither is a guarantee, and both are better than nothing.

## Staging

Each phase is useful on its own, and each one is shippable.

1. **Foundation** — IndexedDB wrapper, the outbox, reconnect detection,
   sync status in the UI. Nothing is cached yet; the outbox just makes
   existing writes survive a dropped connection. Immediately valuable on a
   bad train connection, and it is the load-bearing piece for everything
   after.
2. **Gym offline** — cache drill sets, queue attempts. The easiest surface,
   because attempts are append-only and ungraded. Proves the whole loop end
   to end with nothing at stake.
3. **Read offline** — cache the shelf and bodies. Read-only, so no sync at
   all. Needs the "you've read what you downloaded" state.
4. **Review offline** — the client FSRS port with shared fixtures, the fold
   tables and the client grader, `reviewed_at` and `client_review_id`,
   ordered replay, server re-grade with a disagreement counter. The big one.
5. **Audio packs** — explicit opt-in, size shown, blob storage, quota checks
   and the iOS install gate.

## What we are not doing, and why

- **Starting the native apps for this.** They solve distribution and
  durable storage, not grading or scheduling, and they cost a store review
  per iteration. The shells already exist and will pick this up for free.
- **Running the NLP grader in the browser** (WASM, pyodide, ONNX). Tens of
  megabytes per language before a single card, to replicate something the
  server does correctly. The degraded grader plus authoritative re-grade
  gets most of the value for a few kilobytes.
- **A CRDT or a general sync engine.** The write set is four append-mostly
  kinds with exactly one path-dependent conflict. An ordered outbox with
  idempotency keys is the right size for the problem; a sync engine is a
  second system to debug at altitude.
- **Caching API responses in the service worker.** It looks like a shortcut
  and is a trap: cached JSON has no schema, no versioning, no eviction
  policy and no relationship to the outbox. Offline data belongs in a store
  we control.

## Open questions

- **How much lookahead should a pack carry by default?** 30 days is a guess.
  It should probably be a slider with the resulting size shown live.
- **Where do the fold tables come from?** Deriving them from the existing
  per-language NLP backends is right in principle; whether the backends
  expose enough to do it mechanically is unverified.
- **Multi-device.** Two devices offline with the same card produce two
  review chains for it. Last-writer-wins on the card state loses real
  history. Rare, and worth deciding deliberately rather than discovering.
