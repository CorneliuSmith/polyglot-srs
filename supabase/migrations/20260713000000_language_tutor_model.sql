-- WP15(a): per-language tutor model override.
--
-- NULL = the global default (settings.tutor_model). Admins set this from
-- the Contribute page: high-resource languages can ride a cheaper model
-- while the low-resource differentiator languages stay on the strongest.

ALTER TABLE languages
    ADD COLUMN IF NOT EXISTS tutor_model TEXT;
