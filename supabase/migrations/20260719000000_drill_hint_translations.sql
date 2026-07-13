-- WP17: English drill hints in the learner's language.
--
-- A "from Spanish" learner drilling English grammar reads scaffolding
-- (hint + translation) in Spanish instead of the language they're
-- weakest in. One row per (drill, locale); the drill queries COALESCE
-- these over the English originals when the effective locale matches.
-- Rows are drafts until a per-locale reviewer approves (§3b: content is
-- never self-certified) — unreviewed rows still serve (like the ai_ok
-- draft policy, the beta shows labeled machine-assisted content).
--
-- NOTE (beta freeze, 2026-07-13): committed but NOT applied to the live
-- database yet — the integration harness applies it automatically; apply
-- to production together with the code that reads it.

CREATE TABLE IF NOT EXISTS drill_hint_translations (
    drill_id    UUID NOT NULL REFERENCES drill_sentences(id) ON DELETE CASCADE,
    locale      TEXT NOT NULL,
    hint        TEXT,
    translation TEXT,
    reviewed    BOOLEAN NOT NULL DEFAULT false,
    PRIMARY KEY (drill_id, locale)
);

ALTER TABLE drill_hint_translations ENABLE ROW LEVEL SECURITY;

-- Learner-visible content: readable by any signed-in user; writes happen
-- via the privileged seeder/reviewer paths only.
CREATE POLICY drill_hint_translations_read ON drill_hint_translations
    FOR SELECT TO authenticated USING (true);
