-- Migration: pre-A1 "A0" level for alphabet decks
-- Non-Latin scripts get an Alphabet deck — one studyable card per letter, so a
-- beginner learns to read the script before meeting words. The letters are
-- ordinary vocabulary rows at a new pre-A1 level 'A0', grouped into their own
-- content_list; the CEFR progress bar (A1–C2) simply ignores A0.

ALTER TABLE vocabulary DROP CONSTRAINT vocabulary_level_check;
ALTER TABLE vocabulary ADD CONSTRAINT vocabulary_level_check
    CHECK (level = ANY (ARRAY['A0','A1','A2','B1','B2','C1','C2']));

ALTER TABLE content_lists DROP CONSTRAINT content_lists_level_check;
ALTER TABLE content_lists ADD CONSTRAINT content_lists_level_check
    CHECK (level = ANY (ARRAY['A0','A1','A2','B1','B2','C1','C2']));
