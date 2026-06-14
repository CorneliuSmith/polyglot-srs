-- Migration: Student card feedback
-- Learners can flag a problem with a card they're reviewing ("this sentence
-- looks wrong", "the translation is off"). Feedback is tied to the underlying
-- content (grammar point / vocabulary), not the learner's personal card, so
-- contributors can act on it. Students read/write only their own feedback;
-- contributors/admins read all of it via a privileged connection (after the
-- app-layer role check), the same pattern as grammar content writes.

CREATE TABLE card_feedback (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id  UUID        NOT NULL REFERENCES languages(id),
    card_type    TEXT        NOT NULL CHECK (card_type IN ('grammar', 'vocabulary')),
    content_id   UUID        NOT NULL,   -- grammar_points.id or vocabulary.id
    message      TEXT        NOT NULL,
    status       TEXT        NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'resolved')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_card_feedback_language_status
    ON card_feedback (language_id, status);

ALTER TABLE card_feedback ENABLE ROW LEVEL SECURITY;

CREATE POLICY "card_feedback_insert_own"
    ON card_feedback FOR INSERT WITH CHECK (auth.uid() = user_id);

CREATE POLICY "card_feedback_select_own"
    ON card_feedback FOR SELECT USING (auth.uid() = user_id);
