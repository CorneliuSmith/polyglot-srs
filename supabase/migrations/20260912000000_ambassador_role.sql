-- Ambassador: may create accounts, and nothing else.
--
-- The invite-only beta means every new learner has to be minted by hand, and
-- until now only an admin could do it — so onboarding a class, a study group
-- or a friend's family went through one person. An ambassador is whoever is
-- actually recruiting: they can add accounts without being handed the keys to
-- everything else.
--
-- Scoped DELIBERATELY narrowly. An ambassador CANNOT:
--
--   * list accounts   — GET /contribute/users returns every learner's email
--                       and study volume. "Add one person" and "read the
--                       whole roster" are different powers and one must not
--                       ride along with the other.
--   * delete accounts — permanent and cascades to all of a learner's cards.
--   * grant roles     — otherwise the role escalates to admin in two steps:
--                       make an account, make it an admin.
--   * change plans, touch content, or open the review queue.
--
-- Not a rung on a ladder. Ambassador sits beside contributor and
-- trial_reviewer rather than above or below either: the three grant
-- unrelated powers (recruit / write / check), and an account can hold any
-- combination. Only admin subsumes them all.
--
-- The language_id on the grant is IGNORED for this permission, and the
-- constraint below is where that gets recorded: an account is not per
-- language, so scoping an ambassador to Spanish cannot mean "may only create
-- Spanish accounts" — there is no such thing. The Roles panel says so where
-- an admin is choosing.

ALTER TABLE contributor_roles
    DROP CONSTRAINT IF EXISTS contributor_roles_role_check;
ALTER TABLE contributor_roles
    ADD CONSTRAINT contributor_roles_role_check
    CHECK (role IN (
        'contributor', 'trial_reviewer', 'reviewer', 'ambassador', 'admin'
    ));
