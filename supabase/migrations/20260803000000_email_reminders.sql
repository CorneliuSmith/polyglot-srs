-- Migration: opt-in email review reminders (roadmap: "opt-in reminders")
-- A learner can ask for one email a day when reviews are waiting. Opt-in,
-- with the hour stored in UTC (the client converts from local time), and a
-- last-sent stamp so the sweep sends at most one per day.

ALTER TABLE user_profiles
    ADD COLUMN reminder_opt_in    BOOLEAN     NOT NULL DEFAULT false,
    ADD COLUMN reminder_hour_utc  INT         NOT NULL DEFAULT 16
        CHECK (reminder_hour_utc BETWEEN 0 AND 23),
    ADD COLUMN last_reminder_at   TIMESTAMPTZ;
