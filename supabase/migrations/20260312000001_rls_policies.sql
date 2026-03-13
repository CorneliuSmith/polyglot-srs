-- Migration: Row Level Security Policies
-- Enables RLS on all user data tables and creates per-operation policies.
-- Public content tables (languages, grammar_points, vocabulary, translations,
-- drill_sentences, content_lists) do NOT get RLS -- readable by all authenticated users.

-- ============================================================
-- user_profiles
-- Users can only read/write their own profile row.
-- DELETE is handled by CASCADE from auth.users -- no explicit policy needed.
-- ============================================================
ALTER TABLE user_profiles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_profiles_select_own"
    ON user_profiles
    FOR SELECT
    USING (auth.uid() = id);

CREATE POLICY "user_profiles_insert_own"
    ON user_profiles
    FOR INSERT
    WITH CHECK (auth.uid() = id);

CREATE POLICY "user_profiles_update_own"
    ON user_profiles
    FOR UPDATE
    USING (auth.uid() = id)
    WITH CHECK (auth.uid() = id);

-- ============================================================
-- user_cards
-- Users can only read/write/delete their own SRS cards.
-- ============================================================
ALTER TABLE user_cards ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_cards_select_own"
    ON user_cards
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "user_cards_insert_own"
    ON user_cards
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_cards_update_own"
    ON user_cards
    FOR UPDATE
    USING (auth.uid() = user_id)
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_cards_delete_own"
    ON user_cards
    FOR DELETE
    USING (auth.uid() = user_id);

-- ============================================================
-- review_log
-- Append-only: users can insert and read their own logs.
-- No UPDATE or DELETE policies -- review history is immutable.
-- ============================================================
ALTER TABLE review_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY "review_log_select_own"
    ON review_log
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "review_log_insert_own"
    ON review_log
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

-- ============================================================
-- user_content_subscriptions
-- Users can subscribe/unsubscribe and view their own subscriptions.
-- No UPDATE policy -- use DELETE + INSERT to change subscriptions.
-- ============================================================
ALTER TABLE user_content_subscriptions ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_content_subscriptions_select_own"
    ON user_content_subscriptions
    FOR SELECT
    USING (auth.uid() = user_id);

CREATE POLICY "user_content_subscriptions_insert_own"
    ON user_content_subscriptions
    FOR INSERT
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_content_subscriptions_delete_own"
    ON user_content_subscriptions
    FOR DELETE
    USING (auth.uid() = user_id);
