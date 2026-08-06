# 0003. Offline belongs in the web layer, not in a new native app

- **Date:** 2026-08-06
- **Status:** accepted
- **Touches:** design only — [`docs/offline.md`](../offline.md)

## What we saw

"My friends may need to download packs when they have no internet." Asked
three times, each time framed as a question about whether we have to start
building iOS and Android apps.

## What was actually happening

The question conflated two unrelated things. Offline study needs local
data, local grading and local scheduling. Native apps give you an App Store
listing, push notifications, and a filesystem. Only the last of those is
about offline at all.

The reason the conflation is so natural: on most products the offline
feature *arrives* with the app, so they look like the same decision. Here
they aren't, because the Capacitor shells already bundle the same web build
(`webDir: 'dist'`, no `server.url` — see `docs/native-apps.md`), so anything
built for the browser is already in the apps.

## What we did, and what we didn't

Design offline as a web-layer feature: an IndexedDB pack store, an outbox
for queued writes, a TypeScript port of the FSRS step, and a degraded
client-side grader with authoritative server re-grade on sync.

- **Start the native apps instead** — rejected: the two hard parts (grading,
  scheduling) are the same JavaScript in a WebView, so nothing is bought,
  and each iteration would cost a store review. The sync layer will need
  many iterations in its first month.
- **Run the real NLP grader in the browser** (WASM / pyodide / ONNX) —
  rejected: tens of MB per language before a single card is shown, to
  reproduce something the server already does correctly.
- **A CRDT or a general sync engine** — rejected: the write set is four
  append-mostly kinds with exactly one path-dependent conflict (FSRS
  replay). An ordered outbox with idempotency keys is the right size; a sync
  engine is a second system to debug at 35,000 feet.
- **Cache API responses in the service worker** — rejected, though it looks
  like the shortcut. Cached JSON has no schema, no versioning, no eviction
  policy and no relationship to the outbox.

## What it costs

Storage durability, and only for audio. A text pack is ~2 MB per language
and safe everywhere; a pack with TTS clips is ~85 MB and lives inside a
browser quota that can be evicted under device pressure. On iOS this makes
home-screen installation a precondition rather than a nicety, because
script-writable storage in a plain Safari tab is cleared after seven days
without a visit.

Two backend changes also fall out and are not optional: `/submit` must
accept a `reviewed_at` (replaying a flight's reviews at landing time
computes every interval from the wrong moment), and `review_logs` needs a
unique `client_review_id` so a retried sync cannot double-apply FSRS. The
second is a migration, so the sync endpoint has to probe for the column and
refuse queued reviews rather than accept them unsafely.

## What this is called

An **outbox** (queue writes locally, drain on reconnect) with
**idempotency keys**, plus **optimistic local computation with server
reconciliation** — the client computes a provisional answer, the server
recomputes authoritatively on sync. Standard shape for any offline-capable
app; the same pattern underneath email clients, note apps, and every
point-of-sale terminal that keeps working when the line drops.

## Say it out loud

> Users wanted offline study and everyone assumed that meant building native
> apps. I worked out that the hard parts — language-aware answer grading and
> spaced-repetition scheduling — were pure client-side computation that a
> WebView wouldn't help with, so the only real native advantage was
> non-evictable storage, which mattered only for the audio packs. We built it
> in the web layer, where we could ship daily instead of through App Review,
> and the Capacitor shells picked it up for free. The trade-off was that on
> iOS the pack has to be installed to the home screen or Safari can clear it
> after a week.
