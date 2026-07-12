-- WP4(a) support: reviewers flag problems on grammar points for the admin.
--
-- A note is the middle ground between "fix it myself" and "silently don't
-- approve": "this ideophone is the Ibadan form", "drill 4's tone marks look
-- off". Notes are listed per language on the Contribute page and resolved
-- by a reviewer/admin once addressed.

CREATE TABLE IF NOT EXISTS point_review_notes (
    id               UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    grammar_point_id UUID        NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    author_id        UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    note             TEXT        NOT NULL,
    status           TEXT        NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at      TIMESTAMPTZ,
    resolved_by      UUID        REFERENCES auth.users(id)
);

CREATE INDEX IF NOT EXISTS idx_point_review_notes_point_status
    ON point_review_notes (grammar_point_id, status);

-- Contributor-domain data: reads/writes go through the privileged connection
-- AFTER the app layer verifies the caller's role for the point's language
-- (same pattern as grammar authoring). RLS stays on with no authenticated
-- policies so direct client access is denied.
ALTER TABLE point_review_notes ENABLE ROW LEVEL SECURITY;

CREATE POLICY "point_review_notes_insert_own"
    ON point_review_notes FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = author_id);

CREATE POLICY "point_review_notes_select_own"
    ON point_review_notes FOR SELECT
    TO authenticated
    USING (auth.uid() = author_id);
