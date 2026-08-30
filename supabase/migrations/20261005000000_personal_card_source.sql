-- Personal cards remember where they came from.
--
-- Owner: "can personal cards have sources somewhere - how they were
-- created, etc.?" The creation flow always KNEW (the /cards endpoint takes
-- source: reading|tutor|notes|speak, and hand-written deck cards are their
-- own path) but only used it to pick an auto-filing deck NAME — and decks
-- are renameable, so the provenance was lossy. This stores it.
--
-- NULL means "created before source tracking" and is displayed as such —
-- backfilling a guess would turn an honest unknown into a confident lie.
-- The one safe backfill: a card linked to a note came from notes.

ALTER TABLE user_cloze_cards
    ADD COLUMN IF NOT EXISTS source TEXT
    CHECK (source IS NULL
           OR source IN ('reading', 'tutor', 'notes', 'speak', 'manual'));

UPDATE user_cloze_cards
   SET source = 'notes'
 WHERE source IS NULL AND note_id IS NOT NULL;
