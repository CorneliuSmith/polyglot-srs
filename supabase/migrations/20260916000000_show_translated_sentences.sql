-- Un-hide example sentence translations that were already produced.
--
-- Locale renderings of already-approved English sentences were stored like
-- AI-INVENTED content (reviewed = false), which the card read filters out.
-- So the translations existed but never reached a learner: a fully localized
-- course still showed every example in English.
--
-- Forward-only code cannot repair this. The rows are not merely hidden, they
-- are STUCK: pending_examples skips any sentence that already has a sibling
-- row for the locale, so the loop believes the work is done and never
-- retries. Without this backfill they stay invisible forever.
--
-- Scoped by origin_detail to the two translation paths — the loop
-- ('auto_translate:<locale>') and the CLI's -k translations
-- ('translate:<locale>'). Sentences the AI INVENTED carry a model name
-- instead and keep their review gate.

UPDATE example_sentences
   SET reviewed = true
 WHERE reviewed = false
   AND translation_locale <> 'en'
   AND (origin_detail LIKE 'auto_translate:%' OR origin_detail LIKE 'translate:%');
