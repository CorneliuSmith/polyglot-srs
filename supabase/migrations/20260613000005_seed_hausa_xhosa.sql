-- Migration: Seed Hausa and Xhosa
-- Both written in Latin script (rtl = false): Hausa in Boko orthography
-- (with hooked letters ɓ ɗ ƙ), Xhosa in plain Latin (clicks are c/q/x).
-- Uses ON CONFLICT DO NOTHING for idempotency (safe to re-run).

INSERT INTO languages (code, name, rtl) VALUES
    ('ha', 'Hausa', false),
    ('xh', 'Xhosa', false)
ON CONFLICT (code) DO NOTHING;
