-- WP19(e): tutor mastery suggestions — the tutor stars cards it believes
-- the learner already understands (evidence from the session), and the
-- LEARNER decides: accept advances the card's schedule, dismiss clears the
-- star. Nothing about a card's SRS state ever changes without the learner's
-- confirmation.

CREATE TABLE IF NOT EXISTS tutor_card_suggestions (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    card_id      UUID        NOT NULL REFERENCES user_cards(id) ON DELETE CASCADE,
    language_id  UUID        REFERENCES languages(id),
    item_title   TEXT        NOT NULL,  -- the word / grammar point as the tutor named it
    kind         TEXT        NOT NULL CHECK (kind IN ('vocabulary', 'grammar')),
    evidence     TEXT,                  -- one line of session evidence, shown to the learner
    status       TEXT        NOT NULL DEFAULT 'pending'
                             CHECK (status IN ('pending', 'accepted', 'dismissed')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at  TIMESTAMPTZ
);

-- One live star per card — re-suggesting an unresolved card is a no-op.
CREATE UNIQUE INDEX IF NOT EXISTS idx_tutor_card_suggestions_pending
    ON tutor_card_suggestions (card_id) WHERE status = 'pending';

CREATE INDEX IF NOT EXISTS idx_tutor_card_suggestions_user_lang
    ON tutor_card_suggestions (user_id, language_id, status);

ALTER TABLE tutor_card_suggestions ENABLE ROW LEVEL SECURITY;

CREATE POLICY tutor_card_suggestions_select_own ON tutor_card_suggestions
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY tutor_card_suggestions_insert_own ON tutor_card_suggestions
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY tutor_card_suggestions_update_own ON tutor_card_suggestions
    FOR UPDATE TO authenticated USING (user_id = auth.uid());
