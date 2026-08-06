# 0001. Ask whether a table exists; don't find out by failing

- **Date:** 2026-08-06
- **Status:** accepted
- **Touches:** `backend/services/auto_translate.py` (`table_present`),
  `backend/repositories/trivia.py`, `backend/routers/review.py`

## What we saw

A migration that hadn't been applied yet took down a whole page, not just the
one feature that needed the new table. The `is_visible` column did this once
on the profile endpoint, which every page load hits.

## What was actually happening

Connections come from a pool and each request runs inside **one transaction**
(one all-or-nothing unit of work). In Postgres, a statement naming a table
that doesn't exist doesn't just fail on its own — it puts the whole
transaction into an aborted state, and every later query on that connection
returns "current transaction is aborted" until it rolls back.

So the obvious defence is the wrong one. `try: SELECT … except
UndefinedTableError: fall back` catches the exception and carries on, but the
connection underneath is already poisoned: everything after the fallback
fails too. The code looks defensive and isn't.

## What we did, and what we didn't

Probe first, with a query that is legal whether or not the table exists:
`SELECT to_regclass('public.language_trivia')` returns NULL rather than
raising. If it comes back NULL, the real query is never sent, so the
transaction is never dirtied.

- **try/except around the query** — rejected: catches the error after the
  transaction is already aborted, which is the bug we were fixing.
- **A savepoint around each risky query** — works (a savepoint is a rollback
  point *inside* a transaction), but it means wrapping every read in the
  codebase in ceremony to handle a state that is temporary by definition.
- **Just apply migrations before deploying code** — the right long-term
  answer and not available here: the owner applies migrations by hand with
  `supabase db push`, so there is always a window where new code is live and
  the migration is not.

## What it costs

One extra round-trip per guarded read. The probe result could be cached per
process, but it isn't yet — a cached "missing" would survive the migration
landing and keep the feature dark until a restart, which is a worse failure
than a cheap query.

## What this is called

**Look before you leap** (LBYL) rather than **easier to ask forgiveness than
permission** (EAFP). Python culture defaults hard to EAFP, and that default
is wrong wherever the failure has side effects beyond the failing call —
transactions here, but also file handles, network sockets, and anything with
a state machine behind it.

## Say it out loud

> We had unapplied migrations taking down whole endpoints. It looked like a
> missing try/except, but the real cause was that a failed statement aborts
> the entire Postgres transaction, so catching the error still left the
> connection unusable. I switched to probing with `to_regclass` before the
> query rather than wrapping it in savepoints — the trade-off is an extra
> round-trip on every guarded read.
