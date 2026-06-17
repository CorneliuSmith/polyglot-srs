-- Per-language (and optionally per-user-per-language) FSRS weights.
--
-- FSRS's 19 parameters are fit from review history. A learner rarely has enough
-- personal reviews in one language to fit a stable model, so the default tier is
-- per-language weights pooled across *all* users of that language — available to
-- everyone (including brand-new users) and capturing the language's own
-- forgetting dynamics. A per-user-per-language row can override it once that
-- learner has enough reviews of their own. The scheduler resolves
-- most-specific-first: user_language → language → built-in defaults.

CREATE TABLE fsrs_weights (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    scope         TEXT        NOT NULL CHECK (scope IN ('language', 'user_language')),
    language_id   UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    -- NULL for language-scope rows; set for user_language-scope rows.
    user_id       UUID        REFERENCES auth.users(id) ON DELETE CASCADE,
    params        DOUBLE PRECISION[] NOT NULL,   -- 19 FSRS weights
    review_count  INT         NOT NULL,          -- reviews the fit was based on
    log_loss      DOUBLE PRECISION,              -- fit quality (lower is better)
    fit_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    CHECK (
        (scope = 'language' AND user_id IS NULL)
        OR (scope = 'user_language' AND user_id IS NOT NULL)
    ),
    CHECK (array_length(params, 1) = 19)
);

-- One row per language, and one per (user, language).
CREATE UNIQUE INDEX idx_fsrs_weights_language
    ON fsrs_weights (language_id) WHERE scope = 'language';
CREATE UNIQUE INDEX idx_fsrs_weights_user_language
    ON fsrs_weights (user_id, language_id) WHERE scope = 'user_language';

ALTER TABLE fsrs_weights ENABLE ROW LEVEL SECURITY;

-- Per-language weights are shared content: any authenticated user may read them.
CREATE POLICY fsrs_weights_language_read ON fsrs_weights
    FOR SELECT TO authenticated
    USING (scope = 'language');

-- A user may read only their own per-user weights.
CREATE POLICY fsrs_weights_user_read ON fsrs_weights
    FOR SELECT TO authenticated
    USING (scope = 'user_language' AND user_id = auth.uid());

-- Writes happen only through the optimizer job on the privileged connection,
-- which bypasses RLS; the authenticated role gets no INSERT/UPDATE/DELETE.
