-- Personal decks (owner request): learner-named folders that ORGANIZE
-- personal cloze cards (the ones minted from the Tutor and the Reader).
-- Organization only for now — no learner-authored cards yet; deleting a
-- deck never deletes cards (they just fall back to "unfiled").
CREATE TABLE personal_decks (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id),
    name        TEXT        NOT NULL CHECK (char_length(name) BETWEEN 1 AND 60),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX idx_personal_decks_user_language
    ON personal_decks (user_id, language_id);

ALTER TABLE user_cloze_cards
    ADD COLUMN personal_deck_id UUID REFERENCES personal_decks(id) ON DELETE SET NULL;

ALTER TABLE personal_decks ENABLE ROW LEVEL SECURITY;
CREATE POLICY "personal_decks_select_own" ON personal_decks FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "personal_decks_insert_own" ON personal_decks FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "personal_decks_update_own" ON personal_decks FOR UPDATE USING (auth.uid() = user_id);
CREATE POLICY "personal_decks_delete_own" ON personal_decks FOR DELETE USING (auth.uid() = user_id);

-- Filing a card into a deck is an UPDATE on user_cloze_cards — the table
-- shipped with select/insert/delete policies only.
CREATE POLICY "user_cloze_cards_update_own" ON user_cloze_cards FOR UPDATE USING (auth.uid() = user_id);
