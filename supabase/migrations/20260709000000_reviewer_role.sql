-- Role model buildout: 'reviewer' joins 'contributor' and 'admin'.
--
--   learner      — every account; no row in contributor_roles.
--   contributor  — may draft explanations/points/drills for their language
--                  (language_id NULL = all languages). Drafts stay hidden.
--   reviewer     — may APPROVE content for their language (the human gate
--                  that flips reviewed = true). Scoped like contributor.
--   admin        — everything, everywhere: approve, grant/revoke roles,
--                  set per-language review policy.

-- 'trial_reviewer' is included here even though it isn't introduced until
-- 20260819000000_trial_reviewer.sql, which sets this exact same constraint
-- again later — a deploy that runs the app ahead of its own migrations can
-- accumulate real trial_reviewer grants before that migration ever applies,
-- and a stricter constraint here would then reject that live data on catch-up.
ALTER TABLE contributor_roles
    DROP CONSTRAINT IF EXISTS contributor_roles_role_check;
ALTER TABLE contributor_roles
    ADD CONSTRAINT contributor_roles_role_check
    CHECK (role IN ('contributor', 'trial_reviewer', 'reviewer', 'admin'));

-- Global grants (language_id NULL) must be unique too: the original UNIQUE
-- treats NULLs as distinct, letting duplicate admin rows pile up. Dedupe,
-- then swap in a NULLS NOT DISTINCT constraint (PG15+).
DELETE FROM contributor_roles a
USING contributor_roles b
WHERE a.id > b.id
  AND a.user_id = b.user_id
  AND a.language_id IS NOT DISTINCT FROM b.language_id
  AND a.role = b.role;

ALTER TABLE contributor_roles
    DROP CONSTRAINT IF EXISTS contributor_roles_user_id_language_id_role_key;
ALTER TABLE contributor_roles
    ADD CONSTRAINT contributor_roles_user_id_language_id_role_key
    UNIQUE NULLS NOT DISTINCT (user_id, language_id, role);
