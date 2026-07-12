-- Portuguese (pt): the 17th language. Latin script, default hint layer,
-- full corpus pipeline support (HermitDave + kaikki + Tatoeba por), and a
-- support-locale option for "learning English from Portuguese".
INSERT INTO languages (code, name, rtl) VALUES ('pt', 'Portuguese', false)
ON CONFLICT (code) DO NOTHING;
