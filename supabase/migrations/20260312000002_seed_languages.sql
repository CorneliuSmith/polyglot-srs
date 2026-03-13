-- Migration: Seed Languages
-- Inserts the three launch languages into the languages reference table.
-- Uses ON CONFLICT DO NOTHING for idempotency (safe to re-run).

INSERT INTO languages (code, name, rtl) VALUES
    ('ru', 'Russian', false),
    ('ar', 'Arabic',  true),   -- Arabic is right-to-left
    ('en', 'English', false)
ON CONFLICT (code) DO NOTHING;
