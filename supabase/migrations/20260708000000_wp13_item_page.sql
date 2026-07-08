-- WP13 item-page parity: authorable Related grid + per-user resource read-tracking.
--
-- 1. grammar_points.related — authored [{title, contrast}] entries pointing at
--    other points IN THE SAME LANGUAGE by title (the seeder passes them
--    through; the API resolves titles to ids + the learner's stage at read
--    time, so renames only need a reseed).
-- 2. user_reference_reads — which resource links a learner has marked read,
--    keyed by grammar point + URL (offline book entries key on their title).

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS related JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS user_reference_reads (
    user_id          UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    grammar_point_id UUID        NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    ref_key          TEXT        NOT NULL,  -- the reference's url (online) or title (offline)
    read_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, grammar_point_id, ref_key)
);

ALTER TABLE user_reference_reads ENABLE ROW LEVEL SECURITY;

CREATE POLICY "user_reference_reads_select_own"
    ON user_reference_reads FOR SELECT
    TO authenticated
    USING (auth.uid() = user_id);

CREATE POLICY "user_reference_reads_insert_own"
    ON user_reference_reads FOR INSERT
    TO authenticated
    WITH CHECK (auth.uid() = user_id);

CREATE POLICY "user_reference_reads_delete_own"
    ON user_reference_reads FOR DELETE
    TO authenticated
    USING (auth.uid() = user_id);
