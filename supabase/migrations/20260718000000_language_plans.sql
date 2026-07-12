-- Language plans: a signup chooses Single-language (lower price) or
-- All-languages (higher price). The scope is stored on the profile;
-- 'single' locks active_language_id to plan_language_id (enforced in the
-- profile upsert). Existing accounts are grandfathered as 'all'.
-- Stripe price wiring is WP16 — the scope model ships first so signups
-- capture the choice from day one.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS plan_scope TEXT NOT NULL DEFAULT 'all'
        CHECK (plan_scope IN ('single', 'all')),
    ADD COLUMN IF NOT EXISTS plan_language_id UUID REFERENCES languages(id);
