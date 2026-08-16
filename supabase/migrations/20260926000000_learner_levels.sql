-- Adaptive-sessions stage 1 (docs/plans/adaptive-sessions.md).
--
-- The level a learner CHOSE, stored at last. Until now "your level" was
-- three different derivations (deck subscriptions, card history, placement)
-- and the one the user could set — Settings → Your level — stored nothing:
-- it re-seated deck subscriptions and the AI features never heard about it.
--
-- chosen_level is the floor the prompts must respect (owner's rule: level
-- anchors the session; an explicit ask for harder content is honored ABOVE
-- it, never capped). demonstrated/confidence are stage 3's slots — the
-- rolling estimate from speak errors, tutor corrections and reader gaps —
-- created now so stage 3 needs no second migration.

CREATE TABLE IF NOT EXISTS learner_levels (
    user_id      UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id  UUID NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    chosen_level TEXT CHECK (chosen_level IN ('A1','A2','B1','B2','C1','C2')),
    -- Where the choice came from: 'settings' | 'onboarding' | 'placement'.
    -- Provenance matters when nudging: "you set this yourself in March"
    -- reads differently from "the placement test put you here".
    source       TEXT,
    demonstrated TEXT CHECK (demonstrated IN ('A1','A2','B1','B2','C1','C2')),
    confidence   REAL,
    updated_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, language_id)
);

ALTER TABLE learner_levels ENABLE ROW LEVEL SECURITY;

CREATE POLICY learner_levels_select_own ON learner_levels
    FOR SELECT TO authenticated USING (user_id = auth.uid());
CREATE POLICY learner_levels_insert_own ON learner_levels
    FOR INSERT TO authenticated WITH CHECK (user_id = auth.uid());
CREATE POLICY learner_levels_update_own ON learner_levels
    FOR UPDATE TO authenticated USING (user_id = auth.uid());
