-- The partner's line in the learner's own language, saved with the turn.
--
-- Speak asks for it in the SAME model call that produces the reply (see
-- services/speak.py _TURN_TOOL), so "what did that mean?" is a reveal, not
-- a request: no spinner between the learner and the one sentence they did
-- not understand, and no second call to pay for.
--
-- Nullable on purpose. Turns recorded before this column existed keep
-- their reply and simply have nothing to reveal, and a model response that
-- omits it degrades the same way rather than failing the turn.

ALTER TABLE speak_turns
    ADD COLUMN IF NOT EXISTS partner_translation TEXT;
