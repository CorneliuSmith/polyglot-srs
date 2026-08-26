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

5 tests fail on a clean checkout in this container and are NOT regressions:

- `test_nlp_english.py` (5) — the spaCy English model isn't installed.

**16 tests SKIP when the NLTK WordNet corpus is absent** — 13 in
`test_seeder_english.py` and 3 in `test_seeder_integration.py`. WordNet is
data, not a package: `pip install nltk` doesn't bring it and the English
seeder downloads it on first use, so whether it's present depends on whether
the container's `~/nltk_data` survived and whether nltk's data host was up.
These used to FAIL instead, which read exactly like thirteen broken tests —
CI failed three separate jobs that way in one docs-only pull request. They
now skip (`requires_wordnet` in `backend/tests/conftest.py`). A skip here is
an environment fact; with the corpus present nothing in that set skips, so
real seeder breakage still fails.

Compare against this baseline before claiming a regression. When the count
changes, find out why rather than assuming it's the same 5.

**This baseline was 16, and none of the other 11 were environmental.** Both
causes were test-infrastructure bugs that only appear when the suite is run
the documented way:

1. Eight — across `test_tutor`, `test_reader`, `test_onboarding` and
   `test_contributor` — were `RateLimiter` caching its async Redis client
   against a dead event loop. Each TestClient runs its own loop, so
   whichever file built the client left every later one reading from a
   closed one.
2. Three in `test_audio.py` were `tts_limiter` missing from conftest's
   autouse reset. The cap is 30 calls a minute per user, every test in that
   file uses the same user id, and running the suite as documented sets
   `REDIS_URL` — so the budget lived in Redis and later tests got 429s.

Both looked environmental from outside: they passed alone, passed without
`REDIS_URL`, passed in CI, and the failing set moved with test order. That
is what a shared-state bug looks like, not what a missing key looks like. A
missing key fails the same test every time. Check which shape you have
before filing a failure under "needs a provider".

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

## Production pushes are GATED (owner decision, 26 Aug 2026)

**Do not run the production sequence, and do not propose running it, until
BOTH of these are complete:**

1. the Gym level, and
2. a review of the grammar concepts — which must be **comprehensive**, not
   just defect-free.

The owner has already heard the argument that the deployed app is worse than
the repository and decided the release waits. Do not re-open it each session.
Full detail and the three commands: `docs/decisions/2026-08-26-owner-decisions.md`.

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
