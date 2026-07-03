-- CEFR-style "can-do" function line per grammar point.
--
-- The CEFR inventories (British Council–EAQUALS Core Inventory, English
-- Grammar Profile, Plan Curricular del Instituto Cervantes) describe grammar
-- function-first: what the learner CAN DO with the structure ("say where
-- something is", "talk about ongoing actions"). The grammar path page shows
-- this next to each point so the curriculum reads as communicative goals, not
-- a list of morphology.

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS function_note TEXT;
