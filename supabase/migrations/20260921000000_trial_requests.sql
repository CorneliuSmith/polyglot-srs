-- Trial-access requests (the public front door of the invite-only beta).
--
-- Public signup stays disabled; instead a visitor asks for access from the
-- login page. The request lands here, the admin is emailed (when
-- ADMIN_NOTIFY_EMAIL is set), and the admin panel's queue shows it either
-- way. Approval mints the account with a temporary password that must be
-- reset on first sign-in; the decision is recorded on the row.

CREATE TABLE IF NOT EXISTS trial_requests (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- UNIQUE so a visitor mashing submit (or probing) creates one row ever;
    -- the endpoint answers identically either way.
    email        TEXT        NOT NULL UNIQUE,
    name         TEXT,
    note         TEXT,
    status       TEXT        NOT NULL DEFAULT 'pending'
                 CHECK (status IN ('pending', 'approved', 'rejected')),
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_at   TIMESTAMPTZ,
    decided_by   UUID REFERENCES auth.users (id) ON DELETE SET NULL
);

ALTER TABLE trial_requests ENABLE ROW LEVEL SECURITY;

-- No policies on purpose: the public endpoint writes and the admin queue
-- reads through the privileged connection only. With RLS on and no policy,
-- authenticated users can't read strangers' emails out of this table.
