-- Topic Lens (docs/plans/topic-lens.md, owner-approved taxonomy): a word's
-- semantic bucket, so learners can swap the "what to learn next" axis from
-- CEFR-level decks to meaning-based groups.
--
-- Deliberately the level/level_source shape, not a new deck system: topic
-- "decks" are virtual (computed from this column at read time, scoped to
-- the learner's subscribed level lists), so there is no membership table,
-- no content_lists change, and no new subscription machinery. SRS state
-- stays per-word in user_cards — re-tagging a word can never touch
-- anyone's progress.
--
-- The slug set is FROZEN by owner approval (2026-08-31): it bakes into
-- this CHECK, backend/services/topic_taxonomy.py, frontend's topics map,
-- and the classifier prompt. Display names are i18n and free to reword;
-- changing the SET is a migration plus a re-sort.
--
-- topic_source mirrors level_source: 'ai' is PROVISIONAL until a reviewer
-- confirms (strict-policy languages hide unconfirmed topics from learners;
-- 'ai_ok' languages show them — the same gate as every generated surface).

ALTER TABLE vocabulary
    ADD COLUMN topic TEXT
        CHECK (topic IN (
            -- 22 learner-visible thematic domains. Broad by design: the
            -- interference literature (Tinkham 1993/1997; Waring 1997)
            -- says tight same-category sets (colors, fruits) taught
            -- together blur; loose thematic domains are the safe grain.
            'food_drink', 'home_living', 'family_people',
            'relationships_social', 'body_health', 'clothing_appearance',
            'travel_transport', 'city_places', 'nature_weather_animals',
            'time_dates', 'numbers_measure', 'work_professions',
            'school_learning', 'sports_leisure', 'arts_media',
            'technology', 'communication', 'shopping_money',
            'emotions_mind', 'society_politics', 'religion_culture',
            'science_world',
            -- 2 hidden buckets — every word must classify somewhere, but
            -- nobody wants a deck of "the, of, and". Never rendered in
            -- topic view; the words stay reachable in level view.
            'abstract_general', 'function_words'
        )),
    ADD COLUMN topic_source TEXT
        CHECK (topic_source IN ('ai', 'curated'));

-- The topic summary and topic-scoped learn draw read (language, topic)
-- together; partial because untagged rows (topic IS NULL) are the majority
-- until a course's classification run lands.
CREATE INDEX idx_vocabulary_language_topic
    ON vocabulary (language_id, topic)
    WHERE topic IS NOT NULL;

-- The review queue reads "provisional topics per language" the same way
-- the AI-levels queue reads level_source.
CREATE INDEX idx_vocabulary_language_topic_source
    ON vocabulary (language_id, topic_source)
    WHERE topic_source = 'ai';

-- Bulk topic review writes ONE audit row for the whole (language, bucket)
-- batch — hundreds of per-word rows would bury the log — so the change log
-- learns a 'language' entity kind. Same DROP+ADD shape migration 20260909
-- used to widen this constraint. Safe to couple here: the only writers of
-- 'language' rows are the bulk endpoints, which cannot run until this
-- migration (they touch the topic columns above).
ALTER TABLE content_change_log
    DROP CONSTRAINT IF EXISTS content_change_log_entity_type_check;
ALTER TABLE content_change_log
    ADD CONSTRAINT content_change_log_entity_type_check
    CHECK (entity_type IN
        ('grammar_point', 'drill', 'example_sentence',
         'vocabulary', 'translation', 'language'));
