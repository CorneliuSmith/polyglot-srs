-- A growing bank of language and linguistics trivia, written in the
-- learner's own support language.
--
-- The wait screen's match game plays the words of the session being waited
-- for — which works well once some of that session exists, and not at all
-- at 0%, precisely when someone is most likely to be sitting there. Trivia
-- has no such dependency: it is about language in general, so one question
-- serves every learner who reads that locale, and the bank keeps growing
-- instead of being regenerated per session.
--
-- Deliberately NOT keyed to a course. A question about why writing systems
-- run right-to-left is as good for a Turkish learner as a Greek one, and
-- keying it per course would multiply the same content by ~27.

CREATE TABLE language_trivia (
    id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    locale      TEXT        NOT NULL,
    question    TEXT        NOT NULL,
    options     TEXT[]      NOT NULL CHECK (array_length(options, 1) BETWEEN 2 AND 5),
    -- 0-based index into options.
    answer_index INT        NOT NULL CHECK (answer_index >= 0),
    -- One sentence of payoff shown after answering; this is the part people
    -- actually remember, so it is required rather than decorative.
    fact        TEXT        NOT NULL,
    source      TEXT        NOT NULL DEFAULT 'ai',
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    -- The same question must not enter the bank twice for one locale.
    UNIQUE (locale, question)
);

CREATE INDEX idx_language_trivia_locale ON language_trivia (locale);

-- What each learner has already been asked, so the bank rotates rather than
-- repeating. Rows are cheap and pruning is not worth the complexity.
CREATE TABLE user_trivia_seen (
    user_id    UUID        NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    trivia_id  UUID        NOT NULL REFERENCES language_trivia(id) ON DELETE CASCADE,
    seen_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, trivia_id)
);

-- The bank is shared content: readable by everyone, written by the loop
-- under a privileged connection.
ALTER TABLE language_trivia ENABLE ROW LEVEL SECURITY;
CREATE POLICY "language_trivia_select_all" ON language_trivia
    FOR SELECT USING (true);

ALTER TABLE user_trivia_seen ENABLE ROW LEVEL SECURITY;
CREATE POLICY "user_trivia_seen_select_own" ON user_trivia_seen
    FOR SELECT USING (auth.uid() = user_id);
CREATE POLICY "user_trivia_seen_insert_own" ON user_trivia_seen
    FOR INSERT WITH CHECK (auth.uid() = user_id);
