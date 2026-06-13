-- Migration: Seed Swahili and Turkish
-- Adds the two expansion languages. Both use Latin script (rtl = false).
-- Uses ON CONFLICT DO NOTHING for idempotency (safe to re-run).

INSERT INTO languages (code, name, rtl) VALUES
    ('sw', 'Swahili', false),
    ('tr', 'Turkish', false)
ON CONFLICT (code) DO NOTHING;
