-- Onboarding: mark when a user has completed first-run setup (language choice,
-- placement, and initial content-list subscriptions). NULL = not yet onboarded,
-- which the app uses to route new users into the onboarding flow.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS onboarded_at TIMESTAMPTZ;
