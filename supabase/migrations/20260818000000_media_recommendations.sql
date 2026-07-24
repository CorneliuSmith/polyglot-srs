-- Personalized immersion recommendations (owner request): occasionally suggest
-- books, films, series, and podcasts in the target language, calibrated to the
-- learner's level and interests, to stretch practice beyond the app. Opt-in,
-- gated to paid tutor accounts, generated about once a week.
--
-- Two owner-scoped tables under RLS:
--   media_reco_profile  — one row per learner: the on/off switch plus the
--                         self-description and genre/media-type interests used
--                         to personalize the picks. Global (not per-language).
--   media_recommendations — the history: one row per generated batch, per
--                         language, newest kept forever so the learner can look
--                         back over everything ever suggested.

CREATE TABLE media_reco_profile (
    user_id     UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    enabled     BOOLEAN     NOT NULL DEFAULT false,   -- opt-in; off until turned on
    about       TEXT        NOT NULL DEFAULT '',       -- free-text "about you"
    genres      TEXT[]      NOT NULL DEFAULT '{}',     -- picked genre tags
    media_types TEXT[]      NOT NULL DEFAULT '{}',     -- book/film/series/podcast
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE media_reco_profile ENABLE ROW LEVEL SECURITY;

CREATE POLICY "media_reco_profile_select_own"
    ON media_reco_profile FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "media_reco_profile_insert_own"
    ON media_reco_profile FOR INSERT WITH CHECK (user_id = auth.uid());
CREATE POLICY "media_reco_profile_update_own"
    ON media_reco_profile FOR UPDATE USING (user_id = auth.uid())
    WITH CHECK (user_id = auth.uid());

CREATE TABLE media_recommendations (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id     UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    -- The generated batch: an array of picks, each {type, title, creator, year,
    -- blurb, why, level}. Stored as JSON so the shape can evolve without a
    -- migration and the whole batch reads back in one row.
    items       JSONB       NOT NULL,
    -- The learner's CEFR ceiling at generation time — lets the history show how
    -- picks tracked their growth.
    level       TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- History reads: newest batch for a (learner, language) first.
CREATE INDEX idx_media_reco_user_lang_created
    ON media_recommendations (user_id, language_id, created_at DESC);

ALTER TABLE media_recommendations ENABLE ROW LEVEL SECURITY;

CREATE POLICY "media_recommendations_select_own"
    ON media_recommendations FOR SELECT USING (user_id = auth.uid());
CREATE POLICY "media_recommendations_insert_own"
    ON media_recommendations FOR INSERT WITH CHECK (user_id = auth.uid());
