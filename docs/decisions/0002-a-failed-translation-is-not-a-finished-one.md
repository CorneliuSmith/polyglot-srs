# 0002. A failed translation is not a finished one

- **Date:** 2026-08-06
- **Status:** accepted
- **Touches:** `backend/services/auto_translate.py`,
  `supabase/migrations/20260919000000_translation_attempts.sql`

## What we saw

"Once it fails, it just stops and does nothing." The progress bar reached
some number — 45%, 50% — and stayed there. Reloading didn't help. The only
way out was to abandon the session.

## What was actually happening

Three separate content kinds (grammar metadata, drills, example sentences)
wrote a row *whether or not the model returned anything usable*. An empty
result was recorded exactly like a good one, so the next pass saw the work as
done. The queue drained to zero with nothing in it, and the progress bar,
which measures the queue, stopped moving forever.

The reason it looked like a hang rather than a bug: the loop was healthy the
whole time. It was polling, finding no pending work, and correctly doing
nothing. Nothing was broken except the definition of "pending".

## What we did, and what we didn't

Two changes that only make sense together:

1. **Don't write a row when nothing rendered.** Pending is now defined by the
   content actually being absent (a LEFT JOIN where NULL counts as pending),
   not by a row existing.
2. **Record the attempt separately, in `translation_attempts`, and space
   retries out:** 2 min → 15 min → 1 h → 6 h → 1 day, then daily forever.

Without (2), (1) alone turns a permanently failing item into an infinite hot
loop hammering the provider — which is a worse outage than the one being
fixed, and it takes the healthy items down with it by burning the rate limit.

- **Retry immediately, forever** — rejected: a poisoned item starves every
  good one and provokes the rate limit that stalls the whole fill.
- **Give up after N attempts** — rejected outright by the owner: "failure
  should not be an option." A learner who comes back tomorrow should find the
  work done, not permanently abandoned.
- **A dead-letter queue for hand inspection** — a real option, and where this
  should go if daily retries turn out to be masking bad content rather than
  transient provider errors. Not built: it needs a person to watch it.

## What it costs

A new table, which means a migration the owner has to apply before the retry
ledger does anything. Until then the code degrades quietly — the backoff
clause is only spliced into the SQL when the table has been probed and found
(see 0001), so the loop behaves as it did before rather than crashing. A
permanently broken item now also costs one provider call per day, forever,
instead of none.

## What this is called

**Exponential backoff** with a ceiling, over an **attempt ledger** — the
standard shape for retrying anything across a network. The deeper mistake it
fixes has a name too: **conflating "we tried" with "we succeeded."** Idempotent
retry systems live or die on that distinction, and it is worth being able to
spot it, because it looks like completion from every angle except the one that
matters.

## Say it out loud

> Our background translation fill would stop dead partway through. It looked
> like the worker had crashed, but it was running fine — the bug was that a
> failed generation wrote a row anyway, so the queue counted it as done. I
> made emptiness mean pending and added a separate attempt ledger with
> exponential backoff, because just retrying immediately would have burned
> the rate limit on one poisoned item and starved everything else. The cost
> is a migration and one retry per day per permanently broken item.
