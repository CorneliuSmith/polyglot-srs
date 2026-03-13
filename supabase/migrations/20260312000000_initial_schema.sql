-- Migration: Initial Schema
-- Creates all tables for PolyglotSRS with proper FKs, indexes, and constraints.
-- Public content tables (languages, grammar_points, vocabulary, etc.) have no RLS.
-- User data tables have RLS enabled (see migration 20260312000001_rls_policies.sql).

-- Enable UUID extension if not already present
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ============================================================
-- 1. languages
-- Reference table for all supported study languages.
-- ============================================================
CREATE TABLE languages (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT        NOT NULL UNIQUE,          -- ISO 639-1: 'ru', 'ar', 'en'
    name        TEXT        NOT NULL,                 -- 'Russian', 'Arabic', 'English'
    rtl         BOOLEAN     NOT NULL DEFAULT false,   -- right-to-left script
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 2. grammar_points
-- Grammar concepts ordered by CEFR level with prerequisite chains.
-- ============================================================
CREATE TABLE grammar_points (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id     UUID        NOT NULL REFERENCES languages(id),
    title           TEXT        NOT NULL,
    explanation     TEXT,
    level           TEXT        CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
    display_order   INT         NOT NULL DEFAULT 0,
    prerequisites   UUID[]      NOT NULL DEFAULT '{}',  -- array of grammar_point IDs
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_grammar_points_language_level_order
    ON grammar_points (language_id, level, display_order);

-- ============================================================
-- 3. vocabulary
-- Words with language-specific morphology stored in JSONB.
-- ============================================================
CREATE TABLE vocabulary (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id     UUID        NOT NULL REFERENCES languages(id),
    word            TEXT        NOT NULL,
    reading         TEXT,                              -- pronunciation: furigana, transliteration, tashkeel
    part_of_speech  TEXT,
    level           TEXT        CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
    frequency_rank  INT,
    morphology      JSONB       NOT NULL DEFAULT '{}', -- gender, aspect, root, form, declension, etc.
    alternatives    TEXT[]      NOT NULL DEFAULT '{}', -- regional spellings, aspect partners (NLP-10)
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_vocabulary_language_level
    ON vocabulary (language_id, level);

CREATE INDEX idx_vocabulary_language_frequency
    ON vocabulary (language_id, frequency_rank);

-- ============================================================
-- 4. translations
-- Definitions per vocabulary item per UI locale.
-- Supports multilingual learners: en, ru, ar, es, pt.
-- ============================================================
CREATE TABLE translations (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    vocabulary_id   UUID        NOT NULL REFERENCES vocabulary(id) ON DELETE CASCADE,
    locale          TEXT        NOT NULL,    -- 'en', 'ru', 'ar', 'es', 'pt'
    definition      TEXT        NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (vocabulary_id, locale)
);

CREATE INDEX idx_translations_vocabulary_id
    ON translations (vocabulary_id);

-- ============================================================
-- 5. drill_sentences
-- Fill-in-the-blank sentences linked to grammar points.
-- Multiple rows per grammar_point_id to test concept in varied contexts.
-- ============================================================
CREATE TABLE drill_sentences (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    grammar_point_id    UUID        NOT NULL REFERENCES grammar_points(id) ON DELETE CASCADE,
    vocabulary_id       UUID        REFERENCES vocabulary(id) ON DELETE SET NULL,  -- optional
    sentence            TEXT        NOT NULL,   -- contains {{answer}} marker
    translation         TEXT,                   -- English translation
    hint                TEXT,                   -- optional hint shown to user
    display_order       INT         NOT NULL DEFAULT 0,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_drill_sentences_grammar_point_id
    ON drill_sentences (grammar_point_id);

-- ============================================================
-- 6. content_lists
-- Subscribable level-based lists (e.g. "A1 Grammar (Russian)").
-- Users subscribe to lists to add items to their study queue.
-- ============================================================
CREATE TABLE content_lists (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    language_id     UUID        NOT NULL REFERENCES languages(id),
    list_type       TEXT        NOT NULL CHECK (list_type IN ('grammar', 'vocabulary')),
    level           TEXT        CHECK (level IN ('A1','A2','B1','B2','C1','C2')),
    title           TEXT        NOT NULL,
    description     TEXT,
    display_order   INT         NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (language_id, list_type, level)
);

-- ============================================================
-- 7. user_profiles
-- Per-user settings. PK is auth.users.id (no surrogate key).
-- ============================================================
CREATE TABLE user_profiles (
    id                  UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    batch_size          INT         NOT NULL DEFAULT 5 CHECK (batch_size BETWEEN 1 AND 50),
    ui_language         TEXT        NOT NULL DEFAULT 'en',
    active_language_id  UUID        REFERENCES languages(id),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- 8. user_cards
-- SRS state per card per user. Polymorphic card_id points to
-- grammar_points or vocabulary depending on card_type.
-- ============================================================
CREATE TABLE user_cards (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    language_id     UUID        NOT NULL REFERENCES languages(id),
    card_type       TEXT        NOT NULL CHECK (card_type IN ('grammar', 'vocabulary')),
    card_id         UUID        NOT NULL,    -- polymorphic FK to grammar_points or vocabulary
    ease_factor     FLOAT       NOT NULL DEFAULT 2.5,
    interval        INT         NOT NULL DEFAULT 1,     -- days
    repetitions     INT         NOT NULL DEFAULT 0,
    streak          INT         NOT NULL DEFAULT 0,
    lapses          INT         NOT NULL DEFAULT 0,
    next_review     TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_review     TIMESTAMPTZ,
    is_suspended    BOOLEAN     NOT NULL DEFAULT false,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, card_type, card_id)
);

CREATE INDEX idx_user_cards_user_language_next_review
    ON user_cards (user_id, language_id, next_review);

CREATE INDEX idx_user_cards_user_language_suspended
    ON user_cards (user_id, language_id, is_suspended);

-- ============================================================
-- 9. review_log
-- Immutable append-only record of every review attempt.
-- Enables streaks, heatmaps, and retrospective analytics.
-- ============================================================
CREATE TABLE review_log (
    id                  UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    card_id             UUID        NOT NULL REFERENCES user_cards(id) ON DELETE CASCADE,
    quality             INT         NOT NULL CHECK (quality BETWEEN 0 AND 5),
    ease_factor_before  FLOAT       NOT NULL,
    ease_factor_after   FLOAT       NOT NULL,
    interval_before     INT         NOT NULL,
    interval_after      INT         NOT NULL,
    time_taken_ms       INT,                    -- milliseconds to answer
    answer_result       TEXT,                   -- CORRECT | CORRECT_SLOPPY | WRONG_FORM | WRONG
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_review_log_user_created_at
    ON review_log (user_id, created_at);

-- ============================================================
-- 10. user_content_subscriptions
-- Join table: user subscribes to a content_list to queue items.
-- ============================================================
CREATE TABLE user_content_subscriptions (
    id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    content_list_id UUID        NOT NULL REFERENCES content_lists(id) ON DELETE CASCADE,
    subscribed_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, content_list_id)
);
