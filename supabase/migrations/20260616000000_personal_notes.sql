-- Migration: Personal content — learn from your own input
-- The platform's original differentiator: a learner pastes their own text and
-- turns sentences into fill-in-the-blank (cloze) cards, graded by the same
-- per-language NLP layer and scheduled by the same SRS. Their cards, their
-- context — not just curated frequency lists.
--
-- user_notes        : the raw pasted text (so it isn't lost).
-- user_cloze_cards  : a cloze card authored from that text (sentence with the
--                     {{answer}} blank + the answer + optional translation).
-- user_cards gains a third card_type, 'personal', pointing at user_cloze_cards.
-- All per-user and RLS-scoped to the owner.

CREATE TABLE user_notes (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id),
    title       TEXT,
    content     TEXT        NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_notes_user_language ON user_notes (user_id, language_id);

CREATE TABLE user_cloze_cards (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id),
    sentence    TEXT        NOT NULL,   -- contains the {{answer}} marker
    answer      TEXT        NOT NULL,
    translation TEXT,
    note_id     UUID        REFERENCES user_notes(id) ON DELETE SET NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_user_cloze_cards_user ON user_cloze_cards (user_id, language_id);

-- Allow 'personal' as a card type.
ALTER TABLE user_cards DROP CONSTRAINT IF EXISTS user_cards_card_type_check;
ALTER TABLE user_cards
    ADD CONSTRAINT user_cards_card_type_check
    CHECK (card_type IN ('grammar', 'vocabulary', 'personal'));

-- RLS: owner-only for both tables.
ALTER TABLE user_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_notes_select_own" ON user_notes FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "user_notes_insert_own" ON user_notes FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_notes_delete_own" ON user_notes FOR DELETE USING (auth.uid() = user_id);

ALTER TABLE user_cloze_cards ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_cloze_cards_select_own" ON user_cloze_cards FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "user_cloze_cards_insert_own" ON user_cloze_cards FOR INSERT WITH CHECK (auth.uid() = user_id);
CREATE POLICY "user_cloze_cards_delete_own" ON user_cloze_cards FOR DELETE USING (auth.uid() = user_id);
