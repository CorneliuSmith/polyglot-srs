-- The four plan options (owner: "Make the 4 options … Single language with
-- AI should be the default but provide options to upgrade").
--
-- A plan is a scope (single language / all languages) and, separately,
-- whether AI is included. The scope already lives on user_profiles
-- (plan_scope, plan_language_id). This adds the AI half:
--
--   plan_ai                  — the plan includes the monthly AI pool.
--   plan_ai_subscription_id  — the Stripe subscription that pays for it:
--                              the plan's own when AI was bought as part of
--                              the plan, or a separate add-on subscription
--                              when it was added later. Cancelling that
--                              subscription clears plan_ai and nothing else.
--
-- Why plan-level rather than the per-language tutor_entitlements rows the
-- add-on used to write: "All languages + AI" is one purchase covering every
-- language, and usage is counted per account, not per language. The old
-- per-language rows stay honoured (services/allowance.py) so nothing bought
-- before this loses its pool.
--
-- Reads degrade to false when this migration has not been applied — the
-- profile endpoint probes columns first (backend/routers/auth.py), and the
-- allowance and billing writers probe the same way. /auth/profile is fetched
-- on every page load, so an unguarded new column here takes the app down.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS plan_ai BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS plan_ai_subscription_id TEXT;
