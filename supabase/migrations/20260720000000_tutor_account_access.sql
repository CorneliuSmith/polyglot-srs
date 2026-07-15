-- Per-account tutor access control (admin-set, WP15b).
--
-- The tier system (free monthly / plus daily / operator bypass) prices the
-- tutor; this layer lets the admin override it per person:
--   default — the tiers decide (unchanged behavior).
--   enabled — tutor on regardless of billing entitlement, with an optional
--             per-day message cap (tutor_daily_cap; NULL = the plus tier's
--             daily fair-use number). "Let a friend try it without paying
--             more than N messages a day of API cost."
--   blocked — tutor off for this account, and it wins over EVERYTHING,
--             including the operator's TUTOR_FREE_ACCESS demo bypass.
--
-- NOTE (beta freeze, 2026-07-13): committed but NOT applied to the live
-- database yet — apply together with the code that reads it.

ALTER TABLE user_profiles
    ADD COLUMN IF NOT EXISTS tutor_access TEXT NOT NULL DEFAULT 'default'
        CHECK (tutor_access IN ('default', 'blocked', 'enabled')),
    ADD COLUMN IF NOT EXISTS tutor_daily_cap INT
        CHECK (tutor_daily_cap IS NULL OR tutor_daily_cap >= 0);
