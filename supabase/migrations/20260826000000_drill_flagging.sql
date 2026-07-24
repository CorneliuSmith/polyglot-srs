-- Give grammar drills the same quality-audit flag that vocab example sentences
-- already carry (migration 20260821000000). The --recheck audit walks a point's
-- existing drills, FLAGS the ones the judge rejects (bad grammar, or too trivial
-- to teach), and leaves them for a human — never auto-deletes. A flagged drill
-- is excluded from the audited set on a re-run so it isn't re-judged while a
-- reviewer is handling it.

ALTER TABLE drill_sentences
    ADD COLUMN IF NOT EXISTS flagged     BOOLEAN NOT NULL DEFAULT false,
    ADD COLUMN IF NOT EXISTS flag_reason TEXT;

CREATE INDEX IF NOT EXISTS idx_drill_sentences_flagged
    ON drill_sentences (grammar_point_id) WHERE flagged = true;
