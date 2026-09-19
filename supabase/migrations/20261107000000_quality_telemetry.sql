-- Content-quality telemetry: the tables the quality loop writes and the
-- Content Health panel reads. docs/plans/quality-guardrails-telemetry.md §5.
--
-- Nothing in the repo stored a quality number with a date on it before this:
-- data/quality/baseline.json is a current-state ratchet, reconcile's survey
-- is printed and discarded, db_snapshot overwrites one file. Trend was
-- impossible. These four tables are where every audit run, judge verdict,
-- drift survey and queue depth now lands, keyed by (language, locale) —
-- the support locale is a corpus of its own (§3, principle 6).
--
-- Operator tables: RLS on with no policies, so only the privileged pool role
-- (the app's own connection) reads or writes them — the same shape as
-- grammar_gap_log. Every reader in the app degrades when a table is absent
-- (UndefinedTableError → empty), because migrations are owner-applied and
-- the code deploys first.

-- ---------------------------------------------------------------------------
-- One row per (run, language, locale, metric). The trend source.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quality_runs (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    run_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- audit | judge | reconcile | snapshot | queues | coverage
    kind         TEXT        NOT NULL,
    language_id  UUID        REFERENCES languages(id) ON DELETE CASCADE,
    -- NULL = the course's own content; otherwise the support locale judged
    locale       TEXT,
    -- 'leak_hard', 'unclozable_rows', 'sense.rare', 'gone', 'pending_drills',
    -- 'judge.sense' (coverage) …
    metric       TEXT        NOT NULL,
    value        NUMERIC     NOT NULL,
    -- what the value is out of, when it is a count of a population
    population   INTEGER,
    -- from build_info(); "since the last deploy" needs it
    build_sha    TEXT,
    meta         JSONB       NOT NULL DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS idx_quality_runs_lang_metric_time
    ON quality_runs (language_id, metric, run_at DESC);
CREATE INDEX IF NOT EXISTS idx_quality_runs_kind_time
    ON quality_runs (kind, run_at DESC);
ALTER TABLE quality_runs ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- One row per judged (row, question, locale, run). The evidence and the queue.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS content_verdicts (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    judged_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    run_id       UUID        REFERENCES quality_runs(id) ON DELETE SET NULL,
    language_id  UUID        NOT NULL REFERENCES languages(id) ON DELETE CASCADE,
    locale       TEXT,
    -- vocabulary | example_sentence | drill | grammar_point | translation
    entity_type  TEXT        NOT NULL,
    entity_id    UUID        NOT NULL,
    field        TEXT        NOT NULL,
    -- register | sense | gloss | scripture | card_shape
    question     TEXT        NOT NULL,
    -- the question's own vocabulary, e.g. dialect|classical|msa|unsure
    verdict      TEXT        NOT NULL,
    category     TEXT,
    evidence     TEXT[]      NOT NULL DEFAULT '{}',
    confidence   NUMERIC     NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
    -- the rewrite, or the sense the card should carry
    expected     TEXT,
    note         TEXT,
    -- model id, or local:<model>@host for an OpenAI-compatible endpoint
    judge        TEXT        NOT NULL,
    disposition  TEXT        NOT NULL DEFAULT 'open'
        CHECK (disposition IN ('open', 'accepted', 'rejected', 'fixed', 'superseded')),
    disposed_by  UUID        REFERENCES auth.users(id) ON DELETE SET NULL,
    disposed_at  TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_content_verdicts_lang_q_verdict
    ON content_verdicts (language_id, question, verdict, judged_at DESC);
CREATE INDEX IF NOT EXISTS idx_content_verdicts_entity
    ON content_verdicts (entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_content_verdicts_open
    ON content_verdicts (language_id, disposition) WHERE disposition = 'open';
-- One verdict per (row, question, locale) per run; a re-judge is a new run.
CREATE UNIQUE INDEX IF NOT EXISTS uq_content_verdicts_row_question_run
    ON content_verdicts (entity_type, entity_id, field, question, COALESCE(locale, ''), run_id);
ALTER TABLE content_verdicts ENABLE ROW LEVEL SECURITY;

-- ---------------------------------------------------------------------------
-- The judge's spend controls. A singleton the admin panel edits: the owner's
-- condition for a nightly judge was that the cap is theirs to set, in the
-- app, because it can be a lot of money. Nothing about the judge is a
-- config.py constant.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS quality_settings (
    id                     SMALLINT    PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    -- the master switch; OFF by default, and off when this row is absent
    judge_enabled          BOOLEAN     NOT NULL DEFAULT false,
    -- rows judged per loop cycle (auto_translate_words_per_cycle's shape)
    judge_rows_per_cycle   INTEGER     NOT NULL DEFAULT 200
        CHECK (judge_rows_per_cycle >= 0 AND judge_rows_per_cycle <= 10000),
    -- hard ceiling on tokens the judge may spend in a UTC day; the loop
    -- reads tutor_usage kind='judge' before every batch and stops at it
    judge_daily_token_cap  BIGINT      NOT NULL DEFAULT 1500000
        CHECK (judge_daily_token_cap >= 0),
    -- optional model override for the judge; NULL = the checker tier
    judge_model            TEXT,
    updated_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by             UUID        REFERENCES auth.users(id) ON DELETE SET NULL
);
ALTER TABLE quality_settings ENABLE ROW LEVEL SECURITY;
-- Seeded OFF. ON CONFLICT DO NOTHING: a re-applied migration must not stomp
-- a value an admin later changed (CLAUDE.md, migrations).
INSERT INTO quality_settings (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- ---------------------------------------------------------------------------
-- Per-course targets and the per-course judge opt-in, so "red" is a setting
-- and a language is judged only when an admin switched it on — the same
-- per-language gate auto-translate uses (languages.auto_translate_enabled).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS language_quality_targets (
    language_id         UUID        PRIMARY KEY REFERENCES languages(id) ON DELETE CASCADE,
    judge_enabled       BOOLEAN     NOT NULL DEFAULT false,
    max_bad_card_pct    NUMERIC     NOT NULL DEFAULT 15
        CHECK (max_bad_card_pct >= 0 AND max_bad_card_pct <= 100),
    max_judge_flag_pct  NUMERIC     NOT NULL DEFAULT 5
        CHECK (max_judge_flag_pct >= 0 AND max_judge_flag_pct <= 100),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by          UUID        REFERENCES auth.users(id) ON DELETE SET NULL
);
ALTER TABLE language_quality_targets ENABLE ROW LEVEL SECURITY;
