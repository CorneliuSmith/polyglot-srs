-- Telemetry columns the quality plan's Phase C adds to tables that already
-- exist. docs/plans/quality-guardrails-telemetry.md §5.
--
-- Every addition is nullable with no default, so existing rows and existing
-- writers are untouched; every reader degrades on UndefinedColumnError
-- because migrations are owner-applied and the code deploys first.

-- tutor_usage recorded tokens and nothing about how the call went. The
-- local-model plan needs a fallback counter, the judge loop needs to know
-- whether a batch was rejected by its schema, and nobody has ever been able
-- to answer "how slow is the tutor" from data.
ALTER TABLE tutor_usage
    ADD COLUMN IF NOT EXISTS outcome    TEXT
        CHECK (outcome IS NULL OR outcome IN
               ('ok', 'schema_reject', 'checker_reject', 'error', 'fallback')),
    ADD COLUMN IF NOT EXISTS latency_ms INTEGER
        CHECK (latency_ms IS NULL OR latency_ms >= 0);

-- A learner's "Report an issue" on a grammar card recorded the POINT, not
-- the drill they were looking at, so the sentence was unrecoverable; and no
-- learner channel recorded the locale they were reading in. The beta
-- reviewer's "the Arabic is Egyptian" could never have been a row here —
-- it arrived as a chat message.
ALTER TABLE card_feedback
    ADD COLUMN IF NOT EXISTS field          TEXT
        CHECK (field IS NULL OR field IN
               ('sentence', 'hint', 'translation', 'answer', 'explanation',
                'definition', 'other')),
    -- the drill_sentences.id actually rendered, when the card is a grammar
    -- point; NULL for vocabulary and for rows written before this column
    ADD COLUMN IF NOT EXISTS drill_id       UUID,
    -- the locale overlay the learner was reading (what cards.py served)
    ADD COLUMN IF NOT EXISTS locale         TEXT,
    -- the learner's support_locale at the time, so a report about the
    -- explaining language can be told apart from one about the course
    ADD COLUMN IF NOT EXISTS support_locale TEXT;

-- The reviewer form already captures the field; it did not capture the
-- locale overlay the reviewer was reading, although cards.py serves
-- locale-specific hints and translations.
ALTER TABLE card_change_requests
    ADD COLUMN IF NOT EXISTS locale TEXT;
