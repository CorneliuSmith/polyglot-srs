# 0005. A rollout is a hash, not a coin flip

- **Date:** 2026-08-20
- **Status:** accepted
- **Touches:** `backend/services/experiments.py` (`bucket_of`,
  `variant_for_bucket`, `resolve`, `resolve_variants`),
  `backend/repositories/experiments.py`,
  `supabase/migrations/20260930000000_experiments.sql`,
  `frontend/src/lib/uiSkin.ts`

## What was asked for

> "is it possible for me to get an option in admin to toggle between uis for
> the app? I would prefer feedback from users. Maybe assign a ui to them?
> Broadly this would be for rollout changes? And get feedback?"

Four questions, and only the first one is about a UI switch.

## Why it is not a `ui_skin` column

A column on `user_profiles` answers the first question completely and the
other three not at all. The next rollout — a different Study layout, a new
review flow, a pricing page — would need its own column, its own admin
control, its own feedback plumbing, and its own kill switch, and by the
third one the app would have three near-identical mechanisms that behave
subtly differently under failure.

The generic version costs the same to build once. `experiments` +
`experiment_assignments` + a `variants` JSONB column on `app_feedback`, and
every future rollout is a row.

## The part worth explaining: buckets

The obvious way to roll a change out to 25% of accounts is to draw a random
number per user and store it. That is a write, and the place the answer is
needed is the profile endpoint — which is fetched on **every page load**. A
write there is either a blocked first request or two tabs racing to disagree
about which variant someone is in.

So there is no draw and no storage. The bucket is
`sha256(experiment_key + ":" + user_id) % 100`, computed on the spot. Three
properties fall out of that, and each one is a bug avoided rather than a
nicety:

- **Stable.** The same person lands in the same bucket on every device, in
  every session, across every deploy. Feedback about "the new look" then
  describes an app that person actually saw for a week, rather than one that
  flickered between two designs on alternate page loads.
- **Additive.** Raising 25% to 50% keeps everyone who was already in.
  A stored coin flip re-rolled on a threshold change would eject people
  mid-experiment, which is the one thing guaranteed to poison the answers.
- **Independent per experiment.** Salting the hash with the experiment key
  is not decoration: without it the same low-bucket cohort would be first
  into every change the app ever tries, forever.

## Off beats a pin, which is not the obvious order

`resolve` checks `enabled` **before** the explicit assignment. It is
tempting to let a deliberate pin outrank everything — an admin chose it, on
purpose. But that makes "off" a pause rather than a kill switch: withdrawing
a design would remove it from everyone except the handful of testers who
were pinned to it, leaving the only people still looking at a withdrawn
design as the people whose opinion prompted withdrawing it.

Assignments stay on disk through an off, and take effect again when the
experiment comes back on. Nothing is lost; it is just not in force.

## Feedback is stamped by the server

`app_feedback.variants` is filled from `resolve_variants` inside the
endpoint, not from anything the client posts. A tab left open across a
change would otherwise label the report with a variant the reporter stopped
seeing an hour ago, and a labelled report that is wrong is worse than an
unlabelled one. "The buttons are hard to see" is unusable without the label
and decisive with it.

## The skin has to be removable in one commit

The first experiment is the visual direction, and its non-default variant —
`flat` — is expressed entirely as CSS variable overrides and utility
restyles under `[data-ui="flat"]`. No component knows which skin it is in.
Delete the block and the app is back to Classic with no other edit.

That constraint is what makes it safe to try a look on real accounts. A
rollout you cannot withdraw in one commit is not a rollout, it is a rewrite
with an audience.

## What we didn't do

- **No metrics.** Retention-by-variant is the obvious next thing and
  deliberately absent: the ask was for *feedback*, and a dashboard that
  reports "variant B retains 0.4% better, n=31" invites a decision the
  numbers cannot support at this scale. Sentences from named people are the
  better instrument here, and the app already has a channel for them.
- **No client-side assignment.** The variant is decided server-side and
  arrives with the profile. The browser caches the last answer purely so the
  first frame paints in the right skin; it is never the authority.
- **No automatic ramp.** Percentages move when an admin moves them. A
  scheduler that widened a rollout on its own would need a definition of
  "going well", which is exactly the thing being asked of people instead.

## The industry names for this

Feature flags with **percentage rollout** and **sticky bucketing** — the
hash-based variant is usually called *deterministic bucketing* or
*consistent assignment*, and the same trick appears in consistent hashing
for shard placement. The per-user override is an *allowlist* or *forced
assignment*; the on/off switch is a *kill switch*. Stamping the variant onto
telemetry is *experiment exposure logging*, though here it is attached to
qualitative feedback rather than to events.
