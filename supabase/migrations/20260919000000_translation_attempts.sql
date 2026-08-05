-- An attempt ledger for the auto-translate loop.
--
-- Until now the loop had no way to say "this was tried and did not work".
-- It only had "a rendering exists" or "it does not", so three of the five
-- content kinds recorded a FAILURE as a permanent SUCCESS:
--
--   * a rejected word gloss wrote a translation_reviews row, and
--     pending_words skips any word that has one — forever;
--   * grammar_point_translations got a row even when every field came back
--     empty, and pending_grammar_meta skips any point that has a row;
--   * drill_hint_translations did the same "store NULL to record the
--     attempt", with the same result.
--
-- So one bad batch — a model hiccup, a timeout, a checker in a bad mood —
-- retired that content permanently. The learner saw English forever and
-- nothing in the system knew anything was wrong.
--
-- This table separates "attempted" from "succeeded", so a failure is a
-- reason to wait and try again rather than a reason to stop. Retries back
-- off (see services/auto_translate.RETRY_BACKOFF) so a genuinely
-- impossible item costs a few calls a day, not a hot loop — but it is
-- never abandoned.
--
-- Rows are deleted the moment the content lands, so this stays small: it
-- holds outstanding failures, not history.

CREATE TABLE IF NOT EXISTS translation_attempts (
    -- Matches translation_demand.kind: word | example | drill |
    -- explanation | grammar_meta | gym.
    kind            TEXT        NOT NULL,
    -- The same reference the kind's demand rows use (vocabulary_id,
    -- grammar_point_id, drill_id, language_id). Deliberately no foreign
    -- key: one column cannot reference five tables, and a stale row for
    -- deleted content is swept below.
    ref_id          UUID        NOT NULL,
    locale          TEXT        NOT NULL,
    attempts        INT         NOT NULL DEFAULT 1,
    last_attempt_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- What went wrong last time, for the admin readout. Free text: the
    -- checker's note, or an exception class.
    last_error      TEXT,
    PRIMARY KEY (kind, ref_id, locale)
);

-- The loop's read: "which of these am I allowed to try again yet".
CREATE INDEX IF NOT EXISTS idx_translation_attempts_retry
    ON translation_attempts (kind, locale, last_attempt_at);

ALTER TABLE translation_attempts ENABLE ROW LEVEL SECURITY;

-- Operational data, not learner content: the loop writes it under a
-- privileged connection and nobody reads it through RLS. No policy is
-- deliberate — with RLS on and no policy, authenticated access is denied.
