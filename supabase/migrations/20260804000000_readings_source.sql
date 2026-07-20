-- Harvest loop (WP25d): mark where a reading's text came from, because
-- only app-GENERATED passages may ever be harvested into the shared
-- example-sentence pool. Every existing row was produced by the
-- generator (the Reader has no paste-a-passage mode yet), so the
-- backfill default is correct; if such a mode ever ships it must write
-- source = 'pasted', which the harvester excludes.
ALTER TABLE readings
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'generated';
