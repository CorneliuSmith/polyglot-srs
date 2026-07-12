-- Supabase compatibility shim for local/CI Postgres.
-- The app migrations reference Supabase's auth schema (auth.users, auth.uid())
-- and the 'authenticated' role. This recreates just enough of that surface so
-- the migrations apply and RLS behaves as it does on Supabase.
--
-- auth.uid() reads the user id from request.jwt.claims, exactly as Supabase
-- does, so rls_connection's set_config('request.jwt.claims', ...) drives it.

CREATE EXTENSION IF NOT EXISTS pgcrypto;  -- gen_random_uuid()

CREATE SCHEMA IF NOT EXISTS auth;

CREATE TABLE IF NOT EXISTS auth.users (
    id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT,
    -- mirror the real Supabase columns the admin console reads
    created_at      TIMESTAMPTZ DEFAULT now(),
    last_sign_in_at TIMESTAMPTZ
);
-- pre-shim databases created the two-column shape; upgrade in place
ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ DEFAULT now();
ALTER TABLE auth.users ADD COLUMN IF NOT EXISTS last_sign_in_at TIMESTAMPTZ;

CREATE OR REPLACE FUNCTION auth.uid() RETURNS UUID
LANGUAGE sql STABLE AS $$
    SELECT NULLIF(
        current_setting('request.jwt.claims', true)::jsonb ->> 'sub',
        ''
    )::uuid
$$;

-- The pooled connection runs as the database owner and SET ROLE authenticated;
-- create that role and let it use the public schema.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
        CREATE ROLE authenticated NOLOGIN;
    END IF;
END$$;

GRANT USAGE ON SCHEMA auth TO authenticated;
GRANT EXECUTE ON FUNCTION auth.uid() TO authenticated;
