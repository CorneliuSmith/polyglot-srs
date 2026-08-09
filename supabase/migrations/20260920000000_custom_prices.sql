-- Per-account monthly pricing, set from the admin panel.
--
-- The fixed plans (stripe_price_single / stripe_price_all) charge everyone
-- the same dashboard Price. The owner wants each account's monthly charge
-- under their control — trials, friends, classrooms, early supporters all
-- deserve different numbers — WITHOUT minting a Stripe Price per person.
--
-- A row here overrides the plan pricing for that account: checkout charges
-- monthly_cents through Stripe price_data (an inline price, no dashboard
-- object), and a 0-cent row means the account subscribes free of charge
-- with no Stripe round trip at all. No row = the standard plan prices.

CREATE TABLE IF NOT EXISTS custom_prices (
    user_id       UUID PRIMARY KEY REFERENCES auth.users (id) ON DELETE CASCADE,
    monthly_cents INTEGER     NOT NULL CHECK (monthly_cents >= 0),
    currency      TEXT        NOT NULL DEFAULT 'usd',
    -- Why this account pays this ("beta tester", "classroom deal") — shown
    -- only in the admin panel.
    note          TEXT,
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE custom_prices ENABLE ROW LEVEL SECURITY;

-- A learner may read their own price (the Settings/pricing pages show what
-- they would pay). Writes go through the privileged connection only — the
-- admin endpoint verifies the admin role first.
CREATE POLICY custom_prices_self_read ON custom_prices
    FOR SELECT USING (auth.uid() = user_id);
