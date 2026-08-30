-- One-time AI top-ups (owner: "single purchase ai improvements", priced
-- at $5 for +200 messages after the margin work).
--
-- A top-up ADDS ITS MESSAGES TO THE CURRENT CALENDAR MONTH's allowance —
-- the same window every plan pool uses — which keeps the accounting one
-- SUM over rows in the window instead of a mutable credit ledger. The
-- purchase button says exactly that before charging.
--
-- external_id is the Stripe Checkout session id ('mock' rows come from
-- dev-mock; 'admin:*' rows from a manual grant) and is UNIQUE so webhook
-- retries and double-deliveries grant exactly once.

CREATE TABLE IF NOT EXISTS allowance_topups (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    messages    INT         NOT NULL CHECK (messages > 0),
    external_id TEXT        UNIQUE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_allowance_topups_user_created
    ON allowance_topups (user_id, created_at DESC);

ALTER TABLE allowance_topups ENABLE ROW LEVEL SECURITY;

-- Learners see their own purchases; only the service role writes (grants
-- come from the webhook / dev-mock path on a privileged connection).
CREATE POLICY allowance_topups_select_own ON allowance_topups
    FOR SELECT USING (auth.uid() = user_id);

-- App-wide switches an admin flips at runtime. The first one is the
-- monetization master switch (owner: money features stay off until the
-- employer conflict-of-interest clearance lands, then one toggle turns
-- them on). Everything money-shaped — checkout, upgrade buttons, prices,
-- the tip jar — checks this flag, and a missing table reads as OFF, so a
-- deploy ahead of this migration fails safe: nothing payment-related
-- shows anywhere.
CREATE TABLE IF NOT EXISTS app_flags (
    key        TEXT        PRIMARY KEY,
    enabled    BOOLEAN     NOT NULL DEFAULT false,
    updated_by UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE app_flags ENABLE ROW LEVEL SECURITY;
-- No user-facing policies: reads and writes go through the service role
-- (the API decides what to expose). RLS on with no policy = users see none.

-- Seeded OFF. DO NOTHING so a re-applied migration never stomps the
-- owner's later choice.
INSERT INTO app_flags (key, enabled) VALUES ('monetization', false)
ON CONFLICT (key) DO NOTHING;

-- Pricing v2 (owner: "Remember 7 is without ai enabled"): the single plan's
-- pool becomes 0 — AI arrives via the +$5/mo add-on ('plus', now a pool
-- ADDED to the plan's base) or a one-time top-up. These rows were seeded by
-- 20260907 at the old defaults; updated_by IS NULL plus the old value
-- guards each UPDATE so a number an admin has deliberately changed (edits
-- always stamp updated_by) is never stomped — only the untouched launch
-- default migrates to the new default.
UPDATE plan_message_limits SET monthly_messages = 0, updated_at = now()
WHERE plan = 'single' AND monthly_messages = 100 AND updated_by IS NULL;

UPDATE plan_message_limits SET monthly_messages = 200, updated_at = now()
WHERE plan = 'plus' AND monthly_messages = 1000 AND updated_by IS NULL;
