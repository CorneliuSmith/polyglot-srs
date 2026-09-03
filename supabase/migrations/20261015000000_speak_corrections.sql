-- Speak: "no corrections — I just want to talk".
--
-- A session's mode says WHEN corrections are shown (coach: one per turn;
-- flow: at the end). This flag says whether they are recorded at all. With
-- it off the partner is told to keep no notes, the turn stores none, and
-- the end-of-session breakdown is skipped — nothing to group, no model call
-- (docs/plans/owner-notes-2026-09-03.md, item 2, the optional flag).
--
-- A flag rather than a third mode: `mode` is load-bearing in the summary
-- reader and a third value would touch every branch. Stored per session,
-- like mode, because reading an old session back has to know what the
-- learner was shown. Existing rows read true — every session before this
-- column recorded corrections.
--
-- The code probes for this column (repositories/speak.py) and treats a
-- database without it as "corrections on": a learner who unticks the box
-- on an unmigrated deploy is told so in the start response.

ALTER TABLE speak_sessions
    ADD COLUMN IF NOT EXISTS corrections BOOLEAN NOT NULL DEFAULT true;
