-- Admin-controlled language visibility (owner, 2026-07-27): "I should be
-- able to set which languages are visible." Lets a draft-tier or
-- still-being-built language stay out of onboarding/the language picker
-- without deleting it or touching its content — admins/contributors keep
-- full access via the dedicated admin panel regardless of this flag.
ALTER TABLE languages
    ADD COLUMN IF NOT EXISTS is_visible BOOLEAN NOT NULL DEFAULT true;
