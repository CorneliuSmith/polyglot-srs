-- Migration: AI Tutor entitlements
-- Per-user, per-language access to the AI tutor add-on. Rows are written by
-- the billing pipeline (service role) when a user purchases tutor access;
-- users can only read their own entitlements.

CREATE TABLE tutor_entitlements (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     UUID        NOT NULL REFERENCES languages(id),
    is_active       BOOLEAN     NOT NULL DEFAULT true,
    expires_at      TIMESTAMPTZ,                -- NULL = no expiry (lifetime / managed by billing)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, language_id)
);

CREATE INDEX idx_tutor_entitlements_user
    ON tutor_entitlements (user_id, language_id);

ALTER TABLE tutor_entitlements ENABLE ROW LEVEL SECURITY;

-- Read-only for users; INSERT/UPDATE happen via the service role (billing),
-- which bypasses RLS.
CREATE POLICY "tutor_entitlements_select_own"
    ON tutor_entitlements
    FOR SELECT
    USING (auth.uid() = user_id);
