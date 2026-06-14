-- Migration: Defense-in-depth RLS on contributor-writable content tables
-- grammar_points and drill_sentences are written only through the contribute
-- router's privileged connection (after an app-layer role check). Enabling RLS
-- here makes the database enforce that too: the content is world-readable
-- (SELECT USING true preserves all existing reads), but there is no
-- INSERT/UPDATE/DELETE policy, so the `authenticated` role can never write —
-- only a BYPASSRLS/owner connection (the privileged pool role) can. So a future
-- endpoint that forgets its role check still cannot corrupt content via RLS.
--
-- RLS is enabled, not FORCEd, so the table-owner pool role (which the seeders
-- and privileged_connection use) keeps writing as before.

ALTER TABLE grammar_points ENABLE ROW LEVEL SECURITY;
CREATE POLICY "grammar_points_read_all"
    ON grammar_points FOR SELECT USING (true);

ALTER TABLE drill_sentences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "drill_sentences_read_all"
    ON drill_sentences FOR SELECT USING (true);
