-- "Please fill my language on this course" — the learner's side of the
-- auto-translate toggle (docs: LEARN.md, "Asking for a support language").
--
-- The toggle governs BULK spend, not whether a learner is served: the
-- demand lane always translates what someone is waiting on, and the
-- baseline lane buys a usage-scaled starter corpus even when the course is
-- switched off (services/auto_translate.py). What a switched-off course
-- does NOT get is the full backlog drain, so most of it stays English.
-- That is a real thing to want, and the owner cannot afford every course
-- at once — so learners ask, and the ask is evidence for which course to
-- turn on next.
--
-- One row per (learner, course, locale): asking twice is asking once.
-- Rows are kept after a decision so the next admin can see that the
-- demand was real and already answered.

CREATE TABLE IF NOT EXISTS translation_requests (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users (id) ON DELETE CASCADE,
    language_id  UUID        NOT NULL REFERENCES languages (id) ON DELETE CASCADE,
    -- The support locale asked for, as a language CODE: it is what
    -- user_profiles stores and what the translate loop keys its pairs on.
    locale       TEXT        NOT NULL,
    note         TEXT,
    status       TEXT        NOT NULL DEFAULT 'open'
                 CHECK (status IN ('open', 'fulfilled', 'declined')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at   TIMESTAMPTZ,
    UNIQUE (user_id, language_id, locale)
);

CREATE INDEX IF NOT EXISTS idx_translation_requests_open
    ON translation_requests (language_id, locale)
    WHERE status = 'open';

ALTER TABLE translation_requests ENABLE ROW LEVEL SECURITY;

-- A learner reads and writes their own asks and nobody else's; the admin
-- roll-up reads through the privileged connection, like every other queue.
CREATE POLICY translation_requests_own ON translation_requests
    FOR ALL TO authenticated
    USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());
