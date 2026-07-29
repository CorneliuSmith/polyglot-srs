-- Migration: admin-configurable monthly message allotments per plan tier
--
-- The four tiers (free / single-language / all-languages / tutor+) each had
-- a monthly message cap, but the numbers lived in Settings — an env var,
-- changeable only by redeploying. An admin who wanted to raise the free
-- tier's cap, or trial a different number for a launch, had no lever at
-- all short of asking an engineer to edit config and redeploy.
--
-- No RLS, same as `languages`: every request's allowance check needs to read
-- this (backend/services/allowance.py runs on an ordinary rls_connection),
-- and the numbers carry nothing sensitive. Writes are exposed only through
-- the admin-gated router endpoint (privileged_connection, after the role
-- check) — nothing here as a table-level write policy is a control gap,
-- the same shape as languages.grammar_review_policy already is.

CREATE TABLE IF NOT EXISTS plan_message_limits (
    plan             TEXT        PRIMARY KEY
                                  CHECK (plan IN ('free', 'single', 'all', 'plus')),
    monthly_messages INTEGER     NOT NULL CHECK (monthly_messages >= 0),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by       UUID        REFERENCES auth.users(id) ON DELETE SET NULL
);

-- Seed with today's Settings defaults so applying this migration changes
-- NOTHING until an admin actually edits a number. ON CONFLICT DO NOTHING:
-- a re-apply must never stomp an admin's later edit back to the launch
-- default — same rule every other "initial value" seed in this repo follows.
INSERT INTO plan_message_limits (plan, monthly_messages) VALUES
    ('free',   20),
    ('single', 100),
    ('all',    300),
    ('plus',   1000)
ON CONFLICT (plan) DO NOTHING;
