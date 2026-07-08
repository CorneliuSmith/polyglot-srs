-- Completes the content-table RLS hardening started in
-- 20260614000002: six tables were still UNRESTRICTED, meaning anyone
-- holding the anon key (it ships in the frontend bundle) could read AND
-- WRITE them through Supabase's auto-generated REST API.
--
-- Same posture as the earlier pass: content is world-readable
-- (SELECT USING true preserves every existing read, including the
-- backend's rls_connection queries), and with no INSERT/UPDATE/DELETE
-- policies only the owner/privileged connection (seeders, contribute
-- router) can write. RLS is enabled, not FORCEd, so owner writes work
-- unchanged.

ALTER TABLE languages ENABLE ROW LEVEL SECURITY;
CREATE POLICY "languages_read_all"
    ON languages FOR SELECT USING (true);

ALTER TABLE vocabulary ENABLE ROW LEVEL SECURITY;
CREATE POLICY "vocabulary_read_all"
    ON vocabulary FOR SELECT USING (true);

ALTER TABLE translations ENABLE ROW LEVEL SECURITY;
CREATE POLICY "translations_read_all"
    ON translations FOR SELECT USING (true);

ALTER TABLE example_sentences ENABLE ROW LEVEL SECURITY;
CREATE POLICY "example_sentences_read_all"
    ON example_sentences FOR SELECT USING (true);

ALTER TABLE content_lists ENABLE ROW LEVEL SECURITY;
CREATE POLICY "content_lists_read_all"
    ON content_lists FOR SELECT USING (true);

-- _setup_migrations is setup_db.sh's private bookkeeping (created by the
-- script, not by migrations — hence the existence guard). No policies at
-- all: invisible to the API, owner-only.
DO $$
BEGIN
    IF to_regclass('public._setup_migrations') IS NOT NULL THEN
        EXECUTE 'ALTER TABLE _setup_migrations ENABLE ROW LEVEL SECURITY';
    END IF;
END $$;
