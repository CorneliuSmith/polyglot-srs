# The database: getting your data out, and reproducing it

Three questions: **can I take my data with me?**, **how do I stand up a
copy?**, and **how stuck am I on Supabase?**

Short version: your data comes out with one command and goes back in with
another, onto any Postgres. That round trip runs in CI, so it is tested rather
than promised. Sign-in is the one piece still tied to Supabase.

---

## Taking your data with you

```bash
# Everything you own: all of public, plus your users' rows.
./scripts/backup_db.sh --portable

# Put it anywhere — RDS, Neon, Fly, a container, a laptop.
./scripts/restore_db.sh backups/polyglot-20260729-221521.sql.gz \
    --into postgresql://user:pass@newhost:5432/polyglot --create
```

`restore_db.sh` applies the auth shim first, loads the dump, then verifies —
including a check that no card is left pointing at a missing user. If that
check ever fires the restore exits non-zero rather than leaving you a database
that looks fine and is quietly missing people.

### Why `--portable` and not just `pg_dump`

A plain full dump of a Supabase database also contains Supabase's own schemas
— `storage`, `realtime`, `vault`, `graphql`, `extensions`,
`supabase_functions` — plus all ~15 of GoTrue's `auth` tables. None of that
restores onto a stock Postgres, so such a backup only restores to *another
Supabase*. That is the trap: it looks like a backup right up until the day you
try to leave.

The obvious correction — dump only `public` — is worse in a quieter way. Every
`user_profiles`, `user_cards`, `review_log` and `notes` row has a foreign key
to `auth.users(id)`. Drop those rows and the restore either fails outright or,
with constraints deferred, leaves orphaned learner data.

`--portable` takes exactly what this app owns: all of `public`, plus the
`auth.users` **rows** (not GoTrue's other tables), emitted users-first so the
foreign keys resolve on the way in.

Two bugs were found by actually round-tripping this rather than reasoning
about it: `--clean` emitted a `DROP SCHEMA public` that failed on a pgcrypto
dependency, and `CREATE SCHEMA public` collided with the one every Postgres
ships with. Both are fixed, and
`backend/tests/integration/test_portability.py` now does the whole
dump → restore → verify cycle on every CI run.

### What's in the dump

| | Where it comes from |
|---|---|
| Accounts (`auth.users` rows) | the dump — irreplaceable |
| Learner data: cards, review history, notes, progress, placements | the dump — irreplaceable |
| Roles, feedback, change requests | the dump — irreplaceable |
| Content: vocabulary, grammar, drills, sentences | the dump, and also re-seedable from `data/` |

Content is in there too, so a restore gives you a working app immediately —
but content is the one part you could always rebuild from source with
`setup_db.sh`. The learner data is the part that only exists in the dump.

---

## Reproducing the database

One command, against any Postgres 14+:

```bash
# a local database, created for you
./scripts/setup_db.sh --local

# or an explicit target — RDS, Neon, Fly, a container, Supabase, anything
DATABASE_URL=postgresql://user:pass@host:5432/dbname ./scripts/setup_db.sh

# schema only, no content seeding (fast; good for CI or a smoke test)
./scripts/setup_db.sh --schema-only
```

It is idempotent — re-run it any time. Migrations are tracked in
`_setup_migrations`, so a second run skips what's applied; every seeder
UPSERTs; nothing is destructive.

What it does, in order:

1. **Auth shim, if needed.** Detects whether `auth.uid()` already exists. On
   Supabase it does, so this is skipped. Anywhere else it applies
   `backend/tests/integration/auth_shim.sql`, which recreates the small part
   of Supabase the migrations lean on: `auth.users`, `auth.uid()`, and the
   `authenticated` role.
2. **Migrations**, in filename order, with plain `psql`. The `supabase` CLI
   is never invoked — `supabase db push` is a convenience, not a requirement.
3. **Content seed** — vocabulary, grammar paths, example sentences. Language
   lists are derived from what's in `data/`, not hard-coded, so a language
   you add is picked up without editing the script.
4. **Verify** — row counts, plus a warning if any language's grammar is
   seeded but not yet *visible* (see below).

### Seeded is not the same as visible

The verify step calls this out because it has already caused real confusion.
Under an `ai_ok` publish policy a grammar point needs **both** the policy and
an AI-check verdict before a learner sees it. Seeding sets neither. If the
script prints a "NOT yet visible" note, run:

```bash
python -m backend.services.seeder.generate_grammar --language <code> --ai-check
```

or use **Account → Admin → "Check all now"**, which uses the server's API key
so you need nothing locally. See `docs/seeding.md`.

---

## How coupled to Supabase is this, really?

### Not coupled: the schema

- **No `supabase-py`, no `postgrest`, no client SDK in the backend.** It talks
  to Postgres with `asyncpg` over `DATABASE_URL`. That's it.
- **Migrations are plain SQL.** No CLI, no proprietary DSL, no hosted state.
- **No Supabase-only schema is referenced** — nothing touches `storage.`,
  `realtime.`, `vault.`, `graphql.`. Enforced by
  `backend/tests/integration/test_portability.py`, which fails CI if a new
  migration reaches for one.
- **Every integration test already runs on vanilla Postgres.** The suite you
  run locally is not Supabase.

Verified end to end: all migrations apply to a stock Postgres 16, producing
48 tables and 86 RLS policies with zero schema drift.

### Partly coupled: `auth.users` and RLS

Migrations foreign-key to `auth.users(id)` and RLS policies call `auth.uid()`.
That's Supabase's shape — but it's ~40 lines of it, and `auth_shim.sql`
supplies the same surface anywhere. RLS then behaves identically, because
`auth.uid()` reads `request.jwt.claims`, which the app's `rls_connection`
sets explicitly.

So this is a *convention* borrowed from Supabase, not a dependency on it.

### Genuinely coupled: sign-in

**GoTrue is the real lock-in.** The frontend uses `@supabase/supabase-js` for
login, session refresh, and password reset; the backend validates the JWTs it
issues. Replacing it means:

- an identity provider that issues JWTs with `sub` = the user id (Auth0,
  Clerk, Ory, Keycloak, or your own),
- swapping `frontend/src/lib/supabase.ts` and the auth store for its client,
- pointing JWT verification at the new issuer in `backend/dependencies.py`,
- migrating `auth.users` rows — the shim's table is a superset of what the
  app reads (`id`, `email`, `created_at`, `last_sign_in_at`).

Everything downstream is unaffected: user ids stay the same, so cards,
history and roles all survive untouched.

### Coupled but already optional: TTS storage

Synthesized audio is uploaded to a Supabase storage bucket and served from
its CDN. This is **an optimization with a working fallback** — when the
service key is missing or the upload fails, the clip is returned inline
(base64) and the learner still hears the neural voice. Losing the bucket
costs caching, not audio.

To move it, `_public_url()` and the upload block in `backend/routers/audio.py`
are the only two places that name Supabase; both take a URL and a bearer
token, which is what S3, R2, or GCS want too.

---

## What a full move would take

| Piece | Effort | Notes |
|---|---|---|
| Schema + migrations | **None** | Already portable; `setup_db.sh` applies them anywhere |
| Content (vocab, grammar, sentences) | **None** | Re-seed from `data/`, or `pg_dump`/restore |
| Learner data | **Low** | `pg_dump` — it's ordinary Postgres |
| RLS | **None** | Works as-is via the shim |
| Sign-in | **Real work** | Swap GoTrue for another JWT issuer, migrate `auth.users` |
| TTS storage | **Low** | Two functions; already degrades gracefully |

The order that avoids downtime: `pg_dump` to the new Postgres and point
`DATABASE_URL` at it first (auth still on Supabase, everything keeps
working), then replace sign-in as a separate step.

---

## Backups

`./scripts/backup_db.sh --portable` is the one to keep. A plain
`./scripts/backup_db.sh` is a fuller snapshot and fine for restoring onto the
same platform, but only `--portable` is guaranteed to land somewhere else.

The practical test of not being stuck: if your backup only restores to your
vendor, you are stuck. So restore one somewhere else occasionally — the
scripts make it a two-minute exercise, and a backup nobody has ever restored
is a hypothesis, not a backup.
