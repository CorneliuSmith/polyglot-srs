-- Phase 1 pedagogy analytics: record WHICH sentence was shown for each review.
--
-- Cards now rotate among their example/drill sentences, so the review log needs
-- the actual prompt to make failures analyzable (is the learner failing the
-- word/grammar point, or one particular sentence?). Nullable: older rows and
-- clients that don't send it remain valid.

ALTER TABLE review_log
    ADD COLUMN IF NOT EXISTS prompt_sentence TEXT;
