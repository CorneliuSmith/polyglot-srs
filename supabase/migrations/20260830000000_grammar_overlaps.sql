-- Grammar-point overlap flags (owner request, 2026-07-26): a process that
-- runs alongside the maker-checker recheck and marks pairs of grammar points
-- that teach substantially the same thing, so a reviewer decides — merge
-- them, keep them distinct, or dismiss the flag.
--
-- A dedicated table rather than columns on grammar_points because overlap is
-- a RELATION between two points (one point can overlap several neighbours),
-- with its own lifecycle separate from `reviewed` (human sign-off) and
-- `ai_check_status` (advisory correctness verdict).

CREATE TABLE IF NOT EXISTS grammar_point_overlaps (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id  UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    point_a_id   UUID        NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    point_b_id   UUID        NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    -- duplicate: same content; subsumes: one fully contains the other;
    -- partial: enough shared territory to confuse learners.
    verdict      TEXT        NOT NULL CHECK (verdict IN ('duplicate', 'subsumes', 'partial')),
    reason       TEXT,
    status       TEXT        NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open', 'merged', 'distinct', 'dismissed')),
    detected_by  TEXT,                        -- model id, like origin_detail
    resolved_by  UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    resolved_at  TIMESTAMPTZ,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- Canonical ordering: one row per pair, never (A,B) and (B,A).
    CHECK (point_a_id < point_b_id)
);

-- Re-run idempotency: one OPEN flag per pair; resolved pairs may be
-- re-flagged later if the content drifts back together.
CREATE UNIQUE INDEX IF NOT EXISTS idx_grammar_point_overlaps_open_pair
    ON grammar_point_overlaps (point_a_id, point_b_id)
    WHERE status = 'open';

CREATE INDEX IF NOT EXISTS idx_grammar_point_overlaps_lang_status
    ON grammar_point_overlaps (language_id, status);

-- Same trust model as point_review_notes / content_change_log: no
-- authenticated policies — the app writes via the privileged connection
-- after its own role checks.
ALTER TABLE grammar_point_overlaps ENABLE ROW LEVEL SECURITY;
