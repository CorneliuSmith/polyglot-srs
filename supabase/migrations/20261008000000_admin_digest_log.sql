-- Per-admin send stamp for the operations digest (owner: "I want an email
-- sent to the admin accounts to like the language recommendations").
--
-- The learner digest stamps user_profiles.last_weekly_digest_at; admins
-- need their own, because the two emails answer different questions and an
-- admin is usually also a learner. Its own table rather than another
-- user_profiles column: this is operations state, not a learner setting,
-- and admins are a handful of rows.
--
-- The stamp is written ONLY on an accepted send, so a mail outage retries
-- on the next pass instead of silently eating a day's report.

CREATE TABLE IF NOT EXISTS admin_digest_log (
    user_id      UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    last_sent_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE admin_digest_log ENABLE ROW LEVEL SECURITY;
-- No policies: written by the digest sweep on the service role only.
