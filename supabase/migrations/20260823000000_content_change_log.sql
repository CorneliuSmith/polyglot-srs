-- Content audit log (WP: review-workflow solidification).
--
-- A single append-only timeline of every staff action on a piece of content —
-- who did what, when, and (for edits) the before/after values. This is the
-- audit trail the review workflow lacked: provenance columns only ever stored
-- "last modified by/at" (overwritten, no history) and terminal approval stamps.
--
-- It also powers ROLLBACK: an entry that carries a `before` snapshot can be
-- reverted by re-applying it (which itself logs a 'reverted' entry).
--
-- NB: distinct from `review_log`, which records SRS review *sessions* (a
-- learner grading a card), not content edits.
--
-- Content/admin table: written and read via the privileged connection AFTER an
-- app-layer role check (same pattern as the other review tables). RLS is on
-- with no public policy, so no learner can read or write it directly.

CREATE TABLE IF NOT EXISTS content_change_log (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Monotonic insertion order. now() shares a value across statements in one
    -- transaction, so a strict timeline needs its own sequence to tiebreak.
    seq          BIGINT      GENERATED ALWAYS AS IDENTITY,
    -- What was touched. entity_type is the content kind; entity_id its row id.
    entity_type  TEXT        NOT NULL CHECK (entity_type IN
                     ('grammar_point', 'drill', 'example_sentence',
                      'vocabulary', 'translation')),
    entity_id    UUID        NOT NULL,
    language_id  UUID        REFERENCES languages(id),
    -- Who did it (NULL for a system/automated action, e.g. a CLI recheck flag).
    actor_id     UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    -- What happened: created | edited | ai_checked | flagged | suggested |
    -- approved | rejected | level_set | level_confirmed | reverted | deleted …
    action       TEXT        NOT NULL,
    field        TEXT,                 -- optional: which field, when relevant
    before       JSONB,                -- prior values (enables rollback)
    after        JSONB,                -- new values
    note         TEXT,                 -- reason / change note, when given
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The card-history timeline (newest first) and the per-language audit feed.
CREATE INDEX IF NOT EXISTS idx_content_change_log_entity
    ON content_change_log (entity_type, entity_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_change_log_language
    ON content_change_log (language_id, created_at DESC);

ALTER TABLE content_change_log ENABLE ROW LEVEL SECURITY;
