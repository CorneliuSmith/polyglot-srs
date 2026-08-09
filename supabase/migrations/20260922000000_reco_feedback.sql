-- Learner feedback on recommendation picks (owner request).
--
-- Each pick in a batch can be marked finished (watched / read / listened)
-- and given a 1–5 rating, from the recommendations page. Two jobs:
--   * the page shows what you've already been through, batch by batch;
--   * the engine reads it back — finished/rated titles are never
--     recommended again, and ratings steer the next batch's taste.
--
-- Keyed by (batch, item index) rather than duplicating the pick: the items
-- live as a jsonb array on media_recommendations, and the index is stable
-- because batches are immutable once drafted.

CREATE TABLE IF NOT EXISTS media_reco_feedback (
    user_id    UUID NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    batch_id   UUID NOT NULL REFERENCES media_recommendations (id)
               ON DELETE CASCADE,
    item_index INT  NOT NULL CHECK (item_index >= 0),
    done       BOOLEAN NOT NULL DEFAULT false,
    rating     INT CHECK (rating BETWEEN 1 AND 5),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, batch_id, item_index)
);

ALTER TABLE media_reco_feedback ENABLE ROW LEVEL SECURITY;

-- Owner-scoped both ways: a learner reads and writes their own feedback,
-- nobody else's.
CREATE POLICY reco_feedback_self ON media_reco_feedback
    FOR ALL USING (auth.uid() = user_id) WITH CHECK (auth.uid() = user_id);
