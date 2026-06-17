-- Stripe billing for the tutor add-on.
--
-- Entitlements already gate the tutor (tutor_entitlements, written by the
-- service role). Stripe Checkout + webhooks drive those writes: a completed
-- checkout grants the (user, language) entitlement; a canceled/unpaid
-- subscription revokes it. We track the Stripe customer per user (to reuse it
-- across purchases) and the subscription id on each entitlement (to reconcile
-- subscription lifecycle webhooks back to the row).

CREATE TABLE billing_customers (
    user_id            UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    stripe_customer_id TEXT        NOT NULL UNIQUE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE billing_customers ENABLE ROW LEVEL SECURITY;

-- Users may read their own customer mapping; writes happen via the service
-- role (Stripe flows), which bypasses RLS.
CREATE POLICY billing_customers_select_own ON billing_customers
    FOR SELECT TO authenticated
    USING (user_id = auth.uid());

ALTER TABLE tutor_entitlements
    ADD COLUMN IF NOT EXISTS stripe_subscription_id TEXT,
    ADD COLUMN IF NOT EXISTS stripe_customer_id     TEXT;

-- Webhooks look entitlements up by subscription id to toggle them.
CREATE INDEX IF NOT EXISTS idx_tutor_entitlements_subscription
    ON tutor_entitlements (stripe_subscription_id);
