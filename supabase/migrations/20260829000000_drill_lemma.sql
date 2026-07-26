-- Gym chart + baseline fix: store the dictionary form a drill exercises.
--
-- The Gym attaches the conjugation/declension CHART of the word behind a
-- drill by lemmatizing the inflected answer at serve time — which fails for
-- languages without an NLP backend and for many generated drills, so the
-- chart toggle silently vanishes. The maker KNOWS the dictionary form when
-- it writes the drill; store it, and serving can look the chart up directly.
-- It also anchors the standardized Gym baseline ("word (form)"), letting the
-- serve path swap a bare target-language lemma for its native-language gloss.
-- Nullable: legacy rows fall back to the old lemmatize-the-answer heuristic.

ALTER TABLE drill_sentences
    ADD COLUMN IF NOT EXISTS lemma TEXT;
