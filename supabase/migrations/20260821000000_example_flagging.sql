-- Quality flagging for example sentences (recheck feature).
--
-- The maker-checker CLI gains a --recheck mode that runs an LLM quality judge
-- over EXISTING example sentences (not just gap-fills). A sentence judged bad
-- (unnatural, ungrammatical, doesn't use the target word, or mistranslated) is
-- FLAGGED rather than deleted, so a human reviewer confirms the call. The
-- recheck then tops the word back up to target with fresh alternatives.
--
-- flagged      — set true by the recheck when the judge rejects a sentence.
-- flag_reason  — the judge's short reason, shown to reviewers.
-- A reviewer edit clears the flag (the sentence has been fixed); a delete
-- removes it. Existing rows default to not-flagged.

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS flagged BOOLEAN NOT NULL DEFAULT false;

ALTER TABLE example_sentences
    ADD COLUMN IF NOT EXISTS flag_reason TEXT;

-- Reviewers list a word's flagged sentences first; keep that lookup cheap.
CREATE INDEX IF NOT EXISTS idx_example_sentences_vocab_flagged
    ON example_sentences (vocabulary_id, flagged);
