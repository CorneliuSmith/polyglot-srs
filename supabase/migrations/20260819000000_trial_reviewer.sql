-- Trial (advisory) reviewers: friends who help review WITHOUT publish power.
--
--   trial_reviewer — may open the review queue, curate pending content, and
--                    RECOMMEND approve/reject. Recommendations are advisory:
--                    they never flip reviewed=true. A full reviewer/admin sees
--                    them and makes the real call. Promote to 'reviewer' once
--                    they've shown they're actually doing the work.

ALTER TABLE contributor_roles
    DROP CONSTRAINT IF EXISTS contributor_roles_role_check;
ALTER TABLE contributor_roles
    ADD CONSTRAINT contributor_roles_role_check
    CHECK (role IN ('contributor', 'trial_reviewer', 'reviewer', 'admin'));

-- One advisory recommendation per (reviewer, item). A trial reviewer flags a
-- pending drill or example as approve/reject with an optional note; publishing
-- stays with full reviewers, who see these when they act.
CREATE TABLE review_recommendations (
    id             UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    recommender_id UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id    UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    target_type    TEXT        NOT NULL CHECK (target_type IN ('drill', 'example')),
    target_id      UUID        NOT NULL,
    recommendation TEXT        NOT NULL CHECK (recommendation IN ('approve', 'reject')),
    note           TEXT        NOT NULL DEFAULT '',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (recommender_id, target_type, target_id)
);

CREATE INDEX idx_review_reco_target ON review_recommendations (target_type, target_id);
CREATE INDEX idx_review_reco_language ON review_recommendations (language_id);

ALTER TABLE review_recommendations ENABLE ROW LEVEL SECURITY;

-- A recommender manages their own rows; full reviewers/admins read others'
-- through the privileged connection after an app-layer role check (same pattern
-- as the rest of the contributor content).
CREATE POLICY "review_reco_select_own"
    ON review_recommendations FOR SELECT USING (recommender_id = auth.uid());
CREATE POLICY "review_reco_insert_own"
    ON review_recommendations FOR INSERT WITH CHECK (recommender_id = auth.uid());
CREATE POLICY "review_reco_update_own"
    ON review_recommendations FOR UPDATE USING (recommender_id = auth.uid())
    WITH CHECK (recommender_id = auth.uid());
CREATE POLICY "review_reco_delete_own"
    ON review_recommendations FOR DELETE USING (recommender_id = auth.uid());
