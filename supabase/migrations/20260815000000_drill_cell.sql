-- Persist the paradigm CELL on each drill (gym thickness + adaptation, WP).
--
-- The seed data tags every conjugation/declension drill with the cell it
-- exercises ("yo", "tú", "vosotros"…). Until now that tag was used only for the
-- seed-time density check (≥2 drills per cell) and then dropped. Storing it lets
-- generation fill each cell to a target *balanced* (not pile drills on "yo" and
-- leave "vosotros" thin), and gives the adaptive gym the per-cell signal it
-- needs to weight what a learner has seen vs. keeps missing.
--
-- Null for non-paradigm drills (plain grammar points) and legacy rows — those
-- keep behaving exactly as before.

ALTER TABLE drill_sentences
    ADD COLUMN cell TEXT;

-- Generation and the adaptive rotation both group a point's drills by cell.
CREATE INDEX idx_drill_sentences_point_cell
    ON drill_sentences (grammar_point_id, cell);
