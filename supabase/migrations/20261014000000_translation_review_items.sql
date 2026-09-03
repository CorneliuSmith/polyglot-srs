-- Rejected locale renderings of the NON-vocabulary layers get a review row.
--
-- The maker–checker translates five kinds of text into a learner's support
-- locale: word glosses, drill translations and hints, grammar explanations,
-- grammar titles and notes, and example-sentence meanings. When the checker
-- rejected a GLOSS the proposal landed in translation_reviews (20260731) for
-- an admin to approve, fix or dismiss. When it rejected anything else, the
-- row simply stayed unwritten and the attempt ledger paced a retry: the
-- learner kept reading English and nobody could see why (docs/plans/
-- owner-notes-2026-09-03.md, item 5.2).
--
-- One table for the four other kinds, keyed by (kind, target_id, locale,
-- field): a drill has two fields (translation, hint), a grammar point three
-- (title, culture_note, function_note). `proposed` is the maker's rendering
-- even when the checker rejected it — a queue with nothing to approve is a
-- bin, not a review (same lesson as translation_reviews.proposed).
--
-- Writers probe for this table (services/auto_translate.py) and skip the
-- queue when it is absent, so an unmigrated deploy behaves exactly as
-- before. Admin-only, like translation_reviews; no learner-side policy.

CREATE TABLE IF NOT EXISTS translation_review_items (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    kind        TEXT        NOT NULL CHECK (kind IN ('drill', 'explanation',
                                                    'grammar_meta', 'example')),
    field       TEXT        NOT NULL DEFAULT 'translation',
    target_id   UUID        NOT NULL,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    locale      TEXT        NOT NULL,
    source_text TEXT        NOT NULL,      -- the English being rendered
    proposed    TEXT,                      -- the maker's rendering, if any
    reason      TEXT,                      -- the checker's note
    status      TEXT        NOT NULL DEFAULT 'pending'
                            CHECK (status IN ('pending', 'approved', 'rejected')),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (kind, target_id, locale, field)
);

CREATE INDEX IF NOT EXISTS idx_translation_review_items_lang_status
    ON translation_review_items (language_id, status);

ALTER TABLE translation_review_items ENABLE ROW LEVEL SECURITY;
