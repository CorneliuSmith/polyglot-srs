-- Extend the advisory AI semantic check to vocabulary.
--
-- Grammar points already carry an AI linguist verdict (ai_check_* on
-- grammar_points, migration 20260613000010). Words deserve the same first
-- pass: is the definition accurate, are the example sentences natural and
-- correct? Same shape, same advisory role — it never publishes, it flags
-- concerns for the human reviewer.

ALTER TABLE vocabulary
    ADD COLUMN IF NOT EXISTS ai_check_status TEXT
        CHECK (ai_check_status IN ('pass', 'concerns')),
    ADD COLUMN IF NOT EXISTS ai_check_notes  TEXT,
    ADD COLUMN IF NOT EXISTS ai_checked_at   TIMESTAMPTZ;
