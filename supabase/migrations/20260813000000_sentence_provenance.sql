-- Sentence provenance (WP38 / owner request): track where each drill and
-- example sentence came from, and whether WE have changed it since. This lets
-- reviewers see at a glance what is "ours" vs imported, and gives the planned
-- on-demand generation / paid-ingest pipeline a place to tag its output so
-- generated and hand-edited content is always distinguishable from the seed.
--
-- source vocabulary (free text, but these are the conventions):
--   'seed'     — authored by us in the seed data (the curriculum drills)
--   'human'    — added/authored by a contributor in the app
--   'ai'       — machine-generated (the future maker-checker pipeline)
--   'tatoeba'  — imported from Tatoeba (external; carries a license)
--   'kaikki'   — imported from a kaikki.org Wiktionary extract (external)
--   'imported' — any other external ingest
-- is_modified flips true the first time we edit an imported/seed row, with
-- modified_by / modified_at recording who and when.

ALTER TABLE drill_sentences
    ADD COLUMN source        TEXT        NOT NULL DEFAULT 'seed',
    ADD COLUMN origin_detail TEXT,       -- model id, reference URL, source id…
    ADD COLUMN is_modified   BOOLEAN     NOT NULL DEFAULT false,
    ADD COLUMN modified_by   UUID        REFERENCES auth.users(id),
    ADD COLUMN modified_at   TIMESTAMPTZ;

-- example_sentences already carries `source` (default 'tatoeba') + `license`;
-- add the change-tracking columns for parity.
ALTER TABLE example_sentences
    ADD COLUMN origin_detail TEXT,
    ADD COLUMN is_modified   BOOLEAN     NOT NULL DEFAULT false,
    ADD COLUMN modified_by   UUID        REFERENCES auth.users(id),
    ADD COLUMN modified_at   TIMESTAMPTZ;
