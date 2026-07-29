-- Review Mode: flag the exact words, from anywhere (owner, 2026-07-28).
--
-- Raising a change request meant opening a form, choosing a field from a
-- dropdown, and DESCRIBING which part was wrong in prose. For volunteers
-- reviewing dozens of cards that is real friction, and it loses information:
-- "the sentence is off" doesn't say WHICH clause.
--
-- Reviewers can now select the words themselves — on a card, in a tutor
-- reply, or in a generated reading — and flag that span directly. The quote
-- is what the review board shows, so a reviewer triaging it sees exactly the
-- text their colleague objected to.
ALTER TABLE card_change_requests
    -- The selected span, snapshotted. Deliberately a plain column, not a
    -- pointer: tutor replies and generated readings are not stored content,
    -- so there is nothing to point AT, and even for cards the quote must
    -- survive the edit it asks for.
    ADD COLUMN IF NOT EXISTS quote TEXT,
    -- Where the span sat, and anything surface-specific: character offsets,
    -- the surrounding text, which tutor message, which sentence of a reading.
    -- JSONB because the shape genuinely differs per surface and the board
    -- only ever reads it back whole — this is the one part of the record
    -- with no fixed schema, and it does not need a second database to hold
    -- it. Everything queried, sorted or joined stays a real column.
    ADD COLUMN IF NOT EXISTS quote_context JSONB NOT NULL DEFAULT '{}'::jsonb;

-- Tutor replies and readings are now flaggable, so the board must accept
-- them as targets. Neither has a stable row id — the quote and its context
-- ARE the record, which is why target_id stays nullable.
ALTER TABLE card_change_requests
    DROP CONSTRAINT IF EXISTS card_change_requests_target_type_check;
ALTER TABLE card_change_requests
    ADD CONSTRAINT card_change_requests_target_type_check
    CHECK (target_type IN (
        'grammar_point', 'drill', 'vocabulary', 'example_sentence',
        'tutor_message', 'reading', 'other'
    ));

-- A one-tap flag records a reason chip instead of prose, so `issue` can be
-- short. The 1..2000 bound already allows that; no change needed — noted
-- here so the next reader doesn't go looking for a missing constraint.
