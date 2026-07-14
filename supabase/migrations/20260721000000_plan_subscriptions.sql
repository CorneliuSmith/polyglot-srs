-- WP16: the Stripe subscription behind a language plan.
--
-- user_profiles.plan_scope/plan_language_id stay the ENFORCED plan (what
-- the app checks); this table records which Stripe subscription backs it,
-- so webhooks can reconcile by subscription id. One plan per user.
-- Cancellation deactivates the row but does NOT touch the profile —
-- what a canceled account keeps (free tier shape) is an owner decision
-- still pending (ROADMAP WP16e); beta accounts keep their promised access.
--
-- NOTE (beta freeze, 2026-07-13): committed but NOT applied to the live
-- database yet — apply together with the code that reads it.

CREATE TABLE IF NOT EXISTS plan_subscriptions (
    user_id                 UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    plan_scope              TEXT NOT NULL CHECK (plan_scope IN ('single', 'all')),
    plan_language_id        UUID REFERENCES languages(id),
    stripe_subscription_id  TEXT,
    stripe_customer_id      TEXT,
    is_active               BOOLEAN NOT NULL DEFAULT true,
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_plan_subscriptions_sub
    ON plan_subscriptions (stripe_subscription_id);

ALTER TABLE plan_subscriptions ENABLE ROW LEVEL SECURITY;

-- Users may see their own billing state; all writes happen on the
-- privileged connection (checkout + webhooks).
CREATE POLICY plan_subscriptions_read_own ON plan_subscriptions
    FOR SELECT TO authenticated USING (user_id = auth.uid());
