# Giving Claude (this environment) database access

By default Claude runs in an isolated, ephemeral sandbox with **no access to
your Supabase database** — seeding your DB does not change that. To let Claude
connect (e.g. to smoke-test seeded content or run queries), two things must be
configured in the Claude Code environment.

> ⚠️ **Use a dev/staging or throwaway database, never production.** A
> `DATABASE_URL` is a privileged credential and this environment executes code.
> Point Claude at a disposable copy, with a least-privilege role, and rotate the
> credential afterwards. See
> https://code.claude.com/docs/en/claude-code-on-the-web for how environments,
> secrets, and network policies work.

## What Claude does NOT need access for

The RLS/integration tests and CI **do not need your database**. They spin up a
throwaway Postgres, apply all migrations fresh, and verify tenant isolation and
SQL correctness. That's already wired up:

```bash
# Locally, against any throwaway Postgres:
export INTEGRATION_DATABASE_URL="postgresql://user:pass@localhost:5432/polyglot_test"
python -m pytest backend/tests/integration -q
```

In CI a Postgres service runs them automatically (`.github/workflows/ci.yml`).

## To let Claude reach a real (staging) database

1. **Provision a staging database.** A separate Supabase project (free tier is
   fine) or a plain Postgres. Apply migrations + seed it there, not in prod.

2. **Add the connection string as a secret/env var** in this environment's
   configuration, named `DATABASE_URL` (and `ANTHROPIC_API_KEY` if you want
   Claude to exercise the AI features). Configure these in the environment
   settings, not in committed files.

3. **Allow network egress** to the database host in the environment's network
   policy. Postgres uses port **5432** (or **6543** for Supabase's Supavisor
   pooler). The default policy in this session blocked outbound to Supabase, so
   this step is required — without it the connection just times out.

4. **Verify** from a Claude session:

   ```bash
   psql "$DATABASE_URL" -c "select count(*) from vocabulary;"
   ```

   If that returns a count, Claude can reach the seeded data and run the app's
   queries against it.

## Least-privilege role (recommended)

Instead of the `postgres` superuser, create a scoped role for Claude:

```sql
-- read-only inspection role (safest for "smoke-test the content")
CREATE ROLE claude_ro LOGIN PASSWORD '...';
GRANT USAGE ON SCHEMA public TO claude_ro;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO claude_ro;
```

Use that role's connection string as `DATABASE_URL`. Note: a read-only role
can't run the seeders or the app's write paths — use a broader role only if you
specifically want Claude to write, and only on staging.
