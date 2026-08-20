-- Migration: experiments and per-user variant assignment
--
-- Owner: "is it possible for me to get an option in admin to toggle between
-- uis for the app? I would prefer feedback from users. Maybe assign a ui to
-- them? Broadly this would be for rollout changes? And get feedback?"
--
-- So this is deliberately NOT a `ui_skin` column. A column would answer the
-- first question and none of the others: the next rollout — a new Study
-- layout, a different review flow — would need its own column, its own admin
-- control, and its own feedback plumbing. One generic mechanism costs the
-- same to build once and nothing to reuse.
--
-- Three rules the shape encodes:
--
--   1. An explicit assignment WINS and is permanent until someone changes it.
--      A learner who was shown the new look on Monday must not be shown the
--      old one on Tuesday because a percentage moved — that is not a rollout,
--      it is a fault, and it poisons exactly the feedback the rollout exists
--      to collect.
--   2. Everyone else is bucketed DETERMINISTICALLY from their user id, so a
--      percentage rollout needs no rows at all and no write on the hot path.
--      (The profile endpoint runs on every page load. See services/
--      experiments.py.)
--   3. Feedback records what the person was actually LOOKING at. "The
--      buttons are hard to see" is unusable without it and decisive with it.

CREATE TABLE IF NOT EXISTS experiments (
    key             TEXT        PRIMARY KEY,
    name            TEXT        NOT NULL,
    description     TEXT,
    -- [{"key": "classic", "label": "Classic"}, …] — ordered, because the
    -- admin panel and the learner's switch both render them in this order.
    variants        JSONB       NOT NULL,
    -- What an unassigned, un-bucketed user gets. Also the answer whenever
    -- the experiment is switched off, which is what makes "off" a real
    -- kill switch rather than a state nobody defined.
    default_variant TEXT        NOT NULL,
    -- {"flat": 25} — percent of users, by deterministic bucket. Variants
    -- absent here get nobody; whatever is left over falls to the default.
    rollout         JSONB       NOT NULL DEFAULT '{}'::jsonb,
    enabled         BOOLEAN     NOT NULL DEFAULT false,
    -- Whether a learner may switch themselves in Settings. On for anything
    -- cosmetic: someone who can leave gives better feedback than someone
    -- who is stuck, and an opt-out is the cheapest safety valve there is.
    learner_choice  BOOLEAN     NOT NULL DEFAULT true,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS experiment_assignments (
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    experiment_key  TEXT        NOT NULL REFERENCES experiments(key) ON DELETE CASCADE,
    variant         TEXT        NOT NULL,
    -- Who decided: an admin picked this person, the person picked it
    -- themselves, or a rollout was frozen onto them. Worth storing because
    -- "50 people are on flat" means something different when 45 of them
    -- chose it.
    source          TEXT        NOT NULL DEFAULT 'admin'
                                CHECK (source IN ('admin', 'self', 'rollout')),
    note            TEXT,
    assigned_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, experiment_key)
);

-- The admin panel's counts: "how many people are on each variant".
CREATE INDEX IF NOT EXISTS idx_experiment_assignments_key_variant
    ON experiment_assignments (experiment_key, variant);

-- What the reporter was looking at, as {"ui_skin": "flat"}. JSONB rather
-- than a ui_variant column so the next experiment is recorded too without
-- another migration.
ALTER TABLE app_feedback
    ADD COLUMN IF NOT EXISTS variants JSONB;

ALTER TABLE experiment_assignments ENABLE ROW LEVEL SECURITY;

-- A user reads their own assignment (the profile endpoint runs under RLS)
-- and never writes it directly: every write goes through the app layer,
-- which checks admin rights or that the experiment allows self-service.
DROP POLICY IF EXISTS "experiment_assignments_select_own" ON experiment_assignments;
CREATE POLICY "experiment_assignments_select_own"
    ON experiment_assignments FOR SELECT USING (auth.uid() = user_id);

-- Experiment definitions are not secret and the resolver needs them on the
-- profile path, so they are readable by any signed-in user. Writes are
-- app-layer, admin-only.
ALTER TABLE experiments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "experiments_select_all" ON experiments;
CREATE POLICY "experiments_select_all"
    ON experiments FOR SELECT TO authenticated USING (true);

-- The first experiment: the visual direction. Seeded OFF and defaulting to
-- classic, so applying this migration changes nothing anybody sees until
-- an admin turns it on.
--
-- DO NOTHING, never DO UPDATE: re-applying a migration must not switch a
-- live experiment back off or throw away a rollout percentage an admin set.
INSERT INTO experiments (key, name, description, variants, default_variant,
                         rollout, enabled, learner_choice)
VALUES (
    'ui_skin',
    'Visual direction',
    'Which look the app is wearing. Classic is what shipped; Flat drops the '
    'card shadows and soft corners for ink borders and square edges.',
    '[{"key": "classic", "label": "Classic"},
      {"key": "flat", "label": "Flat (ink borders)"}]'::jsonb,
    'classic',
    '{}'::jsonb,
    false,
    true
)
ON CONFLICT (key) DO NOTHING;
