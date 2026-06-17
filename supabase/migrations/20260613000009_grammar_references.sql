-- Migration: Grammar reference links
-- External readings/sources shown in the grammar review panel (Bunpro-style
-- links to grammar resources). A JSONB array of {title, url}; only http(s)
-- URLs are stored (sanitized in the application layer). Named reference_links
-- to avoid the SQL reserved word "references".

ALTER TABLE grammar_points
    ADD COLUMN IF NOT EXISTS reference_links JSONB NOT NULL DEFAULT '[]';
