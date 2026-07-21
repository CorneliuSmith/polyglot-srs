-- Card change requests (owner request): low-friction, votable suggestions
-- from staff (reviewer / contributor / admin) on any card's sentence, hint,
-- translation, answer, or explanation — raised inline from Learn or Review,
-- triaged on the review board. Learners keep the separate "Report an issue".
--
-- Contributor-domain data: reads/writes go through the privileged connection
-- AFTER the app verifies the caller's role for the card's language (same
-- pattern as point_review_notes / grammar authoring). RLS on with owner-only
-- policies so direct client access is denied.
CREATE TABLE card_change_requests (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    author_id   UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id),
    -- What the request is about. target_id is the point/drill/vocab id when
    -- known; target_label is a human snapshot (the sentence or word) so the
    -- board reads without joining back to live content.
    target_type TEXT        NOT NULL CHECK (target_type IN
                    ('grammar_point', 'drill', 'vocabulary', 'example_sentence', 'other')),
    target_id   UUID,
    target_label TEXT,
    field       TEXT        NOT NULL CHECK (field IN
                    ('sentence', 'hint', 'translation', 'answer', 'explanation', 'other')),
    issue       TEXT        NOT NULL CHECK (char_length(issue) BETWEEN 1 AND 2000),
    suggestion  TEXT,
    status      TEXT        NOT NULL DEFAULT 'open'
                    CHECK (status IN ('open', 'accepted', 'rejected')),
    resolved_by UUID        REFERENCES auth.users(id),
    resolved_at TIMESTAMPTZ,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_change_requests_lang_status
    ON card_change_requests (language_id, status, created_at DESC);

CREATE TABLE card_change_request_votes (
    request_id UUID       NOT NULL REFERENCES card_change_requests(id) ON DELETE CASCADE,
    user_id    UUID       NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    vote       SMALLINT   NOT NULL CHECK (vote IN (-1, 1)),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (request_id, user_id)
);

ALTER TABLE card_change_requests ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ccr_insert_own" ON card_change_requests FOR INSERT
    TO authenticated WITH CHECK (auth.uid() = author_id);
CREATE POLICY "ccr_select_own" ON card_change_requests FOR SELECT
    TO authenticated USING (auth.uid() = author_id);

ALTER TABLE card_change_request_votes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "ccrv_own" ON card_change_request_votes FOR ALL
    TO authenticated USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
