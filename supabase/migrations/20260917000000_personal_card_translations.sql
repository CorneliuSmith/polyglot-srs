-- Locale renderings of a learner's OWN cloze cards.
--
-- user_cloze_cards.translation is a single column with no locale dimension:
-- whatever language the card was minted in, it stayed that way forever. A
-- learner studying Turkish who switched their support language to Spanish
-- kept reading English meaning lines on every personal card, and no part of
-- the system could fix it — there was nowhere to put the Spanish text.
--
-- Unlike course content, this is ONE learner's private material, so the
-- background loop deliberately does not sweep it. It is filled on demand
-- from that learner's own allowance (see routers/personal_decks.py).

CREATE TABLE user_cloze_card_translations (
    cloze_id    UUID        NOT NULL
                REFERENCES user_cloze_cards(id) ON DELETE CASCADE,
    locale      TEXT        NOT NULL,
    translation TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (cloze_id, locale)
);

CREATE INDEX idx_user_cloze_card_translations_locale
    ON user_cloze_card_translations (locale);

-- Private content: readable and writable only by the card's owner.
ALTER TABLE user_cloze_card_translations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "ucct_select_own" ON user_cloze_card_translations
    FOR SELECT USING (EXISTS (
        SELECT 1 FROM user_cloze_cards cc
         WHERE cc.id = cloze_id AND cc.user_id = auth.uid()));

CREATE POLICY "ucct_insert_own" ON user_cloze_card_translations
    FOR INSERT WITH CHECK (EXISTS (
        SELECT 1 FROM user_cloze_cards cc
         WHERE cc.id = cloze_id AND cc.user_id = auth.uid()));

CREATE POLICY "ucct_delete_own" ON user_cloze_card_translations
    FOR DELETE USING (EXISTS (
        SELECT 1 FROM user_cloze_cards cc
         WHERE cc.id = cloze_id AND cc.user_id = auth.uid()));
