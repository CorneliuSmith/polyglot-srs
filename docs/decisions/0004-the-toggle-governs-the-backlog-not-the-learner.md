# 0004. The auto-translate toggle governs the backlog, not the learner

- **Date:** 2026-08-09
- **Status:** accepted
- **Touches:** `backend/services/auto_translate.py` (`_demand_batches`,
  `baseline_pairs`, `run_translation_cycle`)

## What we saw

Every language change showed "0 of 3 cards ready" and never moved. It had
survived several rounds of fixes to the translation loop itself, each of
which made the engine more correct without touching this symptom.

## What was actually happening

The demand queue — the lane that exists because a learner is looking at
English *right now* — was filtered through the course's
`auto_translate_enabled` toggle. Most courses ship switched off, so a
learner switching to one had their demand silently dropped: the wait screen
promised writing the loop was forbidden from doing, and the loop reported
itself healthy because doing nothing was, by its rules, correct.

It looked like a loop bug because a loop bug had been there before. The
matrix tests proved the engine filled every locale from nothing — which is
exactly why the remaining fault had to be in the wiring around the engine,
not in it. Reproduced deployed: an enabled course went ready in ten
seconds; a switched-off one sat at zero forever.

## What we did, and what we didn't

Split the toggle's meaning into three lanes, priority-ordered inside the
same per-cycle budget:

1. **Demand** — a waiting learner is served, whatever the toggle says.
2. **Baseline** — a switched-off course with recently active learners gets
   a starter corpus scaled by usage (150 words per active learner, capped
   at 600, activity window 14 days). Spend follows the people.
3. **Backlog** — the toggle's real job: opting a course into the full
   breadth-first drain.

- **Auto-enable the toggle when a learner arrives** — rejected: it turns
  one curious click into an open-ended spend the admin explicitly declined,
  and there is no natural point at which it turns itself off again.
- **Keep the gate, make the wait screen honest ("translation is off, start
  in English")** — rejected: honest, but it ships the admin's configuration
  problem to the learner, and the owner's requirement was that the course
  simply work.
- **Serve demand but no baseline** — workable, and the first learner then
  waits on every single batch. The baseline is what makes the second
  session, and the second learner, instant.

## What it costs

A switched-off course in real use now costs up to 600 words of translation
spend the admin didn't opt into — bounded, usage-gated, and it stops
entirely when the learners stop coming. The toggle is no longer a hard cost
switch; absence of learners is. The admin panel wording changed to say so.

## What this is called

**Priority lanes with per-lane budgets** — the same shape as QoS in
networking: interactive traffic pre-empts bulk transfer, and bulk transfer
is the thing you cap. The bug itself is a classic **configuration gate on
the wrong lane**: a knob meant to bound background cost quietly bounding
foreground correctness.

## Say it out loud

> Language switching sat at "0 of 3 cards ready" forever and survived
> several fixes to the translation engine. The engine was fine — an admin
> cost toggle was silently filtering the queue that served learners who
> were actively waiting. I split it into three lanes: waiting learners are
> always served, a course in real use gets a usage-capped starter corpus,
> and the toggle now governs only the bulk backlog drain. The trade-off is
> a bounded spend on switched-off courses that stops by itself when the
> learners leave.
