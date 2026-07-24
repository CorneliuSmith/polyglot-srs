-- Suggested translation/description edits for example sentences (recheck follow-up).
--
-- The --recheck audit also judges whether an EXISTING translation (for English,
-- the description) is actually useful to a learner. When it isn't, the audit
-- must NOT overwrite it — a present translation may be human-authored. Instead
-- it stores a PROPOSED replacement here, which a reviewer accepts (applied to
-- `translation`, cleared) or dismisses. This mirrors the flagged/flag_reason
-- pattern: the recheck curates, a human decides.
--
-- suggested_translation — the audit's proposed better translation/description.
-- suggestion_reason     — why the current one was judged weak.

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS suggested_translation TEXT;

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS suggestion_reason TEXT;
