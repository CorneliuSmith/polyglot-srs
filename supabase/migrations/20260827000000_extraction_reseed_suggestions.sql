-- Migration: doc re-seed → suggestion queue (Option B).
--
-- When the extractor re-seeds a vocabulary word a human has already curated,
-- we must NOT overwrite the live card (that would throw away paid-for human
-- review — "money down the drain"). Instead the importer stashes the model's
-- proposed values as a PENDING content_suggestion the reviewer can accept or
-- dismiss, exactly like a contributor-proposed edit. Two things this needs:
--
--   1. A durable "a human owns this card" signal so the importer knows which
--      words to protect. `level_source='curated'` only speaks to the *level*;
--      a definition/POS edit shouldn't be conflated with a confirmed level. So
--      we add a dedicated `vocabulary.curated` flag, set wherever a human
--      confirms or edits a vocab card, and backfilled from existing curated
--      levels so pre-existing human work is protected on the very next reseed.
--
--   2. content_suggestions has to carry SYSTEM-authored proposals (the importer
--      is not a logged-in user) and mark them as doc-sourced so admin can track
--      how often these comparatively expensive AI recommendations get accepted.

-- Every statement below is guarded (IF NOT EXISTS / naturally idempotent):
-- production received a partial hand-apply of this file before it was ever
-- tracked, so a catch-up push must fill the gaps without dying on the parts
-- that already landed. Same reason 20260828/20260830 are guarded.

-- --- vocabulary: the human-owned signal -----------------------------------
ALTER TABLE vocabulary
    ADD COLUMN IF NOT EXISTS curated BOOLEAN NOT NULL DEFAULT false;

-- Existing human-confirmed levels ARE human-owned cards — protect them now.
UPDATE vocabulary SET curated = true WHERE level_source = 'curated';

-- The reseed importer looks up curated words per language before each upsert.
CREATE INDEX IF NOT EXISTS idx_vocabulary_curated
    ON vocabulary (language_id) WHERE curated;

-- --- content_suggestions: system-authored, doc-sourced proposals ----------
-- The importer has no auth.users row, so an extraction proposal has no author.
ALTER TABLE content_suggestions
    ALTER COLUMN author_id DROP NOT NULL;

-- Where the proposal came from: a contributor (the existing flow) or an
-- extraction re-seed (the new doc-sourced flow the metrics count).
ALTER TABLE content_suggestions
    ADD COLUMN IF NOT EXISTS source TEXT NOT NULL DEFAULT 'contributor'
        CHECK (source IN ('contributor', 'extraction'));

-- Free-text provenance for an extraction proposal (e.g. 'document re-seed').
ALTER TABLE content_suggestions
    ADD COLUMN IF NOT EXISTS origin TEXT;

-- Admin acceptance-rate metrics filter by (source, status).
CREATE INDEX IF NOT EXISTS idx_content_suggestions_source_status
    ON content_suggestions (source, status);

-- At most one PENDING extraction proposal per card: a repeated reseed refreshes
-- the existing pending row instead of piling up duplicates.
CREATE UNIQUE INDEX IF NOT EXISTS idx_content_suggestions_one_pending_extraction
    ON content_suggestions (entity_type, entity_id)
    WHERE source = 'extraction' AND status = 'pending';
