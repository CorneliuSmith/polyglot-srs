-- Migration: Seed Yoruba
-- Latin script with tone diacritics and underdotted letters (rtl = false).
-- Uses ON CONFLICT DO NOTHING for idempotency (safe to re-run).

INSERT INTO languages (code, name, rtl) VALUES
    ('yo', 'Yoruba', false)
ON CONFLICT (code) DO NOTHING;
