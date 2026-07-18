-- Migration: Content suggestions (contributor-proposed card edits)
-- A contributor proposes a change to a live card; nothing goes live until a
-- reviewer/admin approves it. The proposal is stored as a field patch
-- (proposed jsonb) against the underlying content (vocabulary / grammar
-- point), so a reviewer can preview and apply it. Same trust model as
-- card_feedback: authors read/write their own; contributors/admins read and
-- resolve all via a privileged connection after the app-layer role check.

CREATE TABLE content_suggestions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id  UUID        NOT NULL REFERENCES languages(id),
    entity_type  TEXT        NOT NULL CHECK (entity_type IN ('vocabulary', 'grammar')),
    entity_id    UUID        NOT NULL,   -- vocabulary.id or grammar_points.id
    author_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    proposed     JSONB       NOT NULL,   -- {definition?, part_of_speech?, usage_note?}
    note         TEXT,                   -- author's rationale
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'approved', 'rejected')),
    reviewer_id  UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    review_note  TEXT,                   -- reviewer's reason on reject
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at  TIMESTAMPTZ
);

CREATE INDEX idx_content_suggestions_language_status
    ON content_suggestions (language_id, status);
CREATE INDEX idx_content_suggestions_entity
    ON content_suggestions (entity_type, entity_id);

ALTER TABLE content_suggestions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "content_suggestions_insert_own"
    ON content_suggestions FOR INSERT WITH CHECK (auth.uid() = author_id);

CREATE POLICY "content_suggestions_select_own"
    ON content_suggestions FOR SELECT USING (auth.uid() = author_id);
