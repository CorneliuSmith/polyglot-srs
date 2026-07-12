-- WP9(b): token/cost capture on the tutor usage log.
--
-- kind distinguishes what the row cost:
--   'chat'    — one answered tutor message (the allowance unit)
--   'summary' — a post-session summarizer run (cost-only; NEVER counts
--               against a learner's allowance)
-- Cache token columns exist because the tutor deliberately prompt-caches
-- its charter block — cached reads are ~10x cheaper than fresh input, so
-- folding them into input_tokens would wildly overstate cost.

ALTER TABLE tutor_usage
    ADD COLUMN IF NOT EXISTS kind TEXT NOT NULL DEFAULT 'chat';
ALTER TABLE tutor_usage
    ADD COLUMN IF NOT EXISTS cache_write_tokens INTEGER;
ALTER TABLE tutor_usage
    ADD COLUMN IF NOT EXISTS cache_read_tokens INTEGER;

-- The admin cost view aggregates by language over a time window.
CREATE INDEX IF NOT EXISTS idx_tutor_usage_lang_time
    ON tutor_usage (language_id, created_at);
