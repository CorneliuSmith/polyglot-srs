-- Migration: weekly review digest + "you have new picks" surfacing
--
-- Email had exactly one shape: a DAILY nudge that fires only when reviews are
-- due. That serves a learner who studies most days and does nothing at all for
-- someone who wants a once-a-week look at how they're doing — and it never
-- carried the recommendations, which are generated weekly and, until now, only
-- discoverable by remembering to open the page.
--
-- So two INDEPENDENT opt-ins, not a mode switch:
--   reminder_opt_in       (existing) — the daily "reviews are waiting" nudge
--   weekly_digest_opt_in  (new)      — a weekly round-up of the week's study
--                                      WITH that week's picks in the email
-- A learner can have either, both, or neither. Both are off by default.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS weekly_digest_opt_in BOOLEAN NOT NULL DEFAULT false,
    -- Day of week to send, 0 = Sunday … 6 = Saturday, matching Postgres's
    -- EXTRACT(DOW). Defaults to Sunday: a week-in-review reads best at the
    -- boundary, and it avoids landing in a Monday-morning inbox pile.
    ADD COLUMN IF NOT EXISTS weekly_digest_dow INT NOT NULL DEFAULT 0
        CHECK (weekly_digest_dow BETWEEN 0 AND 6),
    ADD COLUMN IF NOT EXISTS last_weekly_digest_at TIMESTAMPTZ;

-- When the learner last actually LOOKED at their recommendations. Drives the
-- once-a-week in-app prompt: a batch newer than this stamp is one they have
-- not seen. Kept server-side rather than in localStorage so the prompt does
-- not reappear on every device, and so dismissing it on a phone settles it
-- on a laptop too.
ALTER TABLE media_reco_profile
    ADD COLUMN IF NOT EXISTS last_seen_at TIMESTAMPTZ;
