-- Undo the self-pair answer leak (WP49 follow-up).
--
-- Learning a language THROUGH itself (Spanish course, Spanish support) is a
-- real pair — a gloss becomes a monolingual dictionary entry, and hints and
-- explanations are English text ABOUT the language that should read in it.
-- But a sentence TRANSLATION is different: rendering "The house is big" into
-- the course language reproduces the drill sentence with the blank filled
-- in, handing the learner the answer.
--
-- The loop no longer produces those. This clears the ones it already wrote.
-- Hints are kept — they were always fine.

-- Drill meaning-lines whose locale IS the drill's own course language.
UPDATE drill_hint_translations dht
   SET translation = NULL
  FROM drill_sentences ds
  JOIN grammar_points gp ON gp.id = ds.grammar_point_id
  JOIN languages l ON l.id = gp.language_id
 WHERE dht.drill_id = ds.id
   AND dht.locale = l.code
   AND dht.translation IS NOT NULL;

-- Machine-written example-sentence siblings in the course's own language.
-- Scoped to this loop's own output (source='ai' + its origin tag) so a
-- human-authored or CLI-generated row is never touched.
DELETE FROM example_sentences es
 USING languages l
 WHERE l.id = es.language_id
   AND es.translation_locale = l.code
   AND es.source = 'ai'
   AND es.origin_detail = 'auto_translate:' || l.code;
