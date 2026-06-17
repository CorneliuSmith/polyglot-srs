-- Migration: Seed Spanish, Italian, French, German, Catalan, Māori
-- All Latin-script (rtl = false). Well-documented languages added so quality
-- can be reviewed across familiar languages. ON CONFLICT DO NOTHING for
-- idempotency.

INSERT INTO languages (code, name, rtl) VALUES
    ('es', 'Spanish',  false),
    ('it', 'Italian',  false),
    ('fr', 'French',   false),
    ('de', 'German',   false),
    ('ca', 'Catalan',  false),
    ('mi', 'Māori',    false)
ON CONFLICT (code) DO NOTHING;
