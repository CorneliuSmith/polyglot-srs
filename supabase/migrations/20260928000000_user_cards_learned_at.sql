-- When a card was LEARNED, as distinct from when its row appeared.
--
-- The Learn tile's "N learned today" counted user_cards.created_at, which
-- is the moment the card was first OFFERED, not the moment it was learned.
-- Those differ by design: a walkthrough left unfinished stays suspended
-- and is re-taught by the next batch (see _vocab_candidates), and the
-- re-teach keeps the original row — so a learner who finished five lessons
-- today, four of them re-taught, was credited with one. The same column
-- also counted cards created today and then abandoned, so the number could
-- be wrong in both directions at once.
--
-- learned_at is stamped when a card ENTERS THE REVIEW QUEUE, which is what
-- "learned" means in this app: teach → check → queue.
--
-- Backfilled from created_at for cards already in the queue, so existing
-- learners' history and daily counts read exactly as they did before.
-- Suspended cards are deliberately left NULL: they have not been learned.

ALTER TABLE user_cards ADD COLUMN IF NOT EXISTS learned_at TIMESTAMPTZ;

UPDATE user_cards
   SET learned_at = created_at
 WHERE learned_at IS NULL
   AND NOT is_suspended;

-- The dashboard asks "which of this user's cards entered the queue today",
-- once per page load.
CREATE INDEX IF NOT EXISTS idx_user_cards_learned_at
    ON user_cards (user_id, language_id, learned_at);
