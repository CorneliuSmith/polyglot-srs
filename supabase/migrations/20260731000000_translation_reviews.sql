-- Migration: Translation review queue
-- The maker–checker translation pipeline auto-applies glosses the checker
-- approved; the ones it rejected land here for a human instead of going live.
-- One pending row per (English word, target locale). Content/admin table —
-- reviewed via the privileged connection after an app-layer role check, like
-- card_feedback; no learner ever reads it, so RLS is on with no public policy.

CREATE TABLE translation_reviews (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_id UUID        NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    locale        TEXT        NOT NULL,   -- the support language the gloss is IN
    proposed      TEXT,                   -- maker's gloss (may be empty on reject)
    reason        TEXT,                   -- checker's note
    status        TEXT        NOT NULL DEFAULT 'pending'
                              CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vocabulary_id, locale)
);

CREATE INDEX idx_translation_reviews_locale_status
    ON translation_reviews (locale, status);

ALTER TABLE translation_reviews ENABLE ROW LEVEL SECURITY;
