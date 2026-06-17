-- Migration: Contributor roles
-- Lets language specialists author grammar explanations in-app. A role is
-- per-language (language_id = NULL means all languages); 'admin' can approve
-- submissions and grant roles. Contributor submissions land unreviewed
-- (grammar_points.reviewed = false) and an admin promotes them.
--
-- Authorization is enforced in the application layer (the contribute router
-- checks roles before writing via a privileged connection). Roles are
-- readable only by their owner.

CREATE TABLE contributor_roles (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id  UUID        REFERENCES languages(id),   -- NULL = all languages
    role         TEXT        NOT NULL CHECK (role IN ('contributor', 'admin')),
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, language_id, role)
);

CREATE INDEX idx_contributor_roles_user ON contributor_roles (user_id);

ALTER TABLE contributor_roles ENABLE ROW LEVEL SECURITY;

CREATE POLICY "contributor_roles_select_own"
    ON contributor_roles FOR SELECT USING (auth.uid() = user_id);

-- Track who last submitted a grammar explanation, for the approval queue.
ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS explanation_submitted_by UUID REFERENCES auth.users(id);

-- Bootstrap the first admin out-of-band (service role / SQL), e.g.:
--   INSERT INTO contributor_roles (user_id, role) VALUES ('<auth-user-id>', 'admin');
