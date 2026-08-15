# Working agreements

## Shipping

**Open a pull request and merge it by default.** Standing authorization from
the owner — do not ask "shall I open a PR?" or "shall I merge?" each time.
Finish a piece of work, verify it, push, open the PR, merge it.

The bar for merging is unchanged by this:

- Frontend `npm run build` clean and `npx vitest run` green. **`npm run build`,
  not `npx tsc --noEmit`** — the build runs `tsc -b`, which type-checks the
  whole project graph and catches errors `--noEmit` silently lets through.
  A green `--noEmit` has already produced a red CI once: four real type
  errors, including a prefetch reading a field that doesn't exist on the
  type it was given, so it warmed nothing and nobody noticed.
- Backend `.venv/bin/pytest backend/tests` at or better than the known
  baseline (see below), and `.venv/bin/ruff check backend/` clean.
- CI green on the PR before merging. A red build is a reason to stop and fix,
  not to merge anyway — "merge by default" removes the question, not the
  standard.

Say so plainly if something is merged with a known gap, rather than letting
the merge imply it was clean.

### Known-failing backend tests (environment, not the code)

8 tests fail on a clean checkout in this container and are NOT regressions:

- `test_nlp_english.py` (5) — the spaCy English model isn't installed.
- `test_audio.py` (3) — needs a live `ANTHROPIC_API_KEY` / provider.

Compare against this baseline before claiming a regression. When the count
changes, find out why rather than assuming it's the same 8.

This baseline was 16 until the rate limiter stopped caching a Redis client
against a dead event loop (`services/rate_limit.RateLimiter.reset`). Eight
of those "environmental" failures — across `test_tutor`, `test_reader`,
`test_onboarding` and `test_contributor` — were that bug, not a missing
key: each TestClient runs its own event loop, and whichever test file first
built the async client left every later one reading from a closed one. It
looked environmental because the failing set moved whenever test order did.
Worth remembering the next time a failure is filed under "needs a provider"
on the strength of it failing here and passing in CI.

### Running the full backend suite

Integration tests skip silently without a database — that once hid ~79 tests
and made a "1244 passing" report meaningless. Start both services first:

```bash
su postgres -c '/usr/lib/postgresql/16/bin/pg_ctl -D /var/tmp/pgtest -o "-p 5433" -l /var/tmp/pgtest.log start'
redis-server --port 6380 --daemonize yes
INTEGRATION_DATABASE_URL="postgresql://postgres@127.0.0.1:5433/postgres" \
REDIS_URL="redis://127.0.0.1:6380/0" .venv/bin/pytest backend/tests -q
```

Postgres in this container gets reaped periodically. If a run produces a
flood of connection errors, restart it and re-run — don't report the flood
as a result.

## Migrations

Migrations are applied by the owner (`supabase db push`), not by this agent.
Any code that reads a newly added table or column must degrade rather than
crash when the migration hasn't landed yet — catch `UndefinedTableError` /
`UndefinedColumnError` and fall back. This matters most for anything on a
hot path: the profile endpoint is fetched on every page load, so an
unguarded new column there takes down the whole app rather than one setting.
The `is_visible` outage taught this once already.

Seeded initial values use `ON CONFLICT DO NOTHING`, never `DO UPDATE` — a
re-applied migration must not stomp a value an admin later changed.
