"""The language-shaped morphology builders (§3b): each language extracts
what ITS learners need per part of speech from kaikki forms arrays."""

from backend.services.seeder.morphology_charts import (
    BUILDERS,
    strip_nominal_chips,
)


def _entry(pos, forms, expansion=""):
    e = {"word": "x", "pos": pos,
         "forms": [{"form": f, "tags": t} for f, t in forms]}
    if expansion:
        e["head_templates"] = [{"expansion": expansion}]
    return e


def _chart(m, title):
    return next((c for c in m.get("charts", []) if c["title"] == title), None)


def _chip(m, label):
    return next((c["value"] for c in m.get("chips", []) if c["label"] == label), None)


class TestRussian:
    def test_verb_gets_aspect_pair_and_conjugation(self):
        m = BUILDERS["ru"](_entry("verb", [
            ("говори́ть", ["canonical", "imperfective"]),
            ("сказа́ть", ["perfective"]),
            ("говорю́", ["first-person", "present", "singular"]),
            ("говори́шь", ["second-person", "present", "singular"]),
            ("говори́т", ["third-person", "present", "singular"]),
            ("говори́м", ["first-person", "present", "plural"]),
            ("говори́л", ["masculine", "past", "singular"]),
            ("говори́ла", ["feminine", "past", "singular"]),
            ("говори́ло", ["neuter", "past", "singular"]),
            ("говори́ли", ["past", "plural"]),
            ("говори́", ["imperative", "second-person", "singular"]),
            ("говори́те", ["imperative", "second-person", "plural"]),
        ]))
        assert _chip(m, "Aspect") == "imperfective"
        assert _chip(m, "Perfective pair") == "сказа́ть"
        assert _chart(m, "Present")["rows"][0] == ["я", "говорю́"]
        assert len(_chart(m, "Past")["rows"]) == 4
        assert _chart(m, "Imperative")["rows"] == [
            ["ты", "говори́"], ["вы", "говори́те"]]

    def test_perfective_verb_charts_future_not_present(self):
        m = BUILDERS["ru"](_entry("verb", [
            ("сказа́ть", ["canonical", "perfective"]),
            ("скажу́", ["first-person", "future", "singular"]),
            ("ска́жешь", ["second-person", "future", "singular"]),
            ("ска́жет", ["third-person", "future", "singular"]),
        ]))
        assert _chart(m, "Future") is not None
        assert _chart(m, "Present") is None

    def test_noun_gets_gender_animacy_declension(self):
        m = BUILDERS["ru"](_entry("noun", [
            ("кни́га", ["canonical", "feminine", "inanimate"]),
            ("кни́га", ["nominative", "singular"]),
            ("кни́ги", ["nominative", "plural"]),
            ("кни́ги", ["genitive", "singular"]),
            ("книг", ["genitive", "plural"]),
            ("кни́ге", ["dative", "singular"]),
            ("кни́гу", ["accusative", "singular"]),
        ]))
        assert _chip(m, "Gender") == "feminine"
        assert _chip(m, "Animacy") == "inanimate"
        decl = _chart(m, "Declension")
        assert decl["columns"] == ["", "Singular", "Plural"]
        assert decl["rows"][0] == ["Nom.", "кни́га", "кни́ги"]


class TestRomance:
    def test_spanish_verb_core_tenses(self):
        persons = ["first-person", "second-person", "third-person"]
        forms = []
        for tense, stem in (("present", "habl"), ("preterite", "hablé"),
                            ("imperfect", "hablaba"), ("future", "hablaré")):
            for p in persons:
                for n in ("singular", "plural"):
                    forms.append((f"{stem}-{p}-{n}", ["indicative", tense, p, n]))
        forms.append(("hablando", ["gerund"]))
        forms.append(("hablado", ["participle", "past"]))
        m = BUILDERS["es"](_entry("verb", forms))
        assert _chip(m, "Gerund") == "hablando"
        assert _chip(m, "Past participle") == "hablado"
        present = _chart(m, "Present")
        assert present["rows"][0][0] == "yo"
        assert len(present["rows"]) == 6
        assert _chart(m, "Preterite") is not None

    def test_noun_gender_and_plural(self):
        m = BUILDERS["es"](_entry("noun", [
            ("casa", ["canonical", "feminine"]),
            ("casas", ["plural"]),
        ]))
        assert _chip(m, "Gender") == "feminine"
        assert _chip(m, "Plural") == "casas"


class TestGerman:
    def test_noun_triple(self):
        m = BUILDERS["de"](_entry("noun", [
            ("Hauses", ["genitive"]),
            ("Häuser", ["plural"]),
        ], expansion="Haus n (strong, genitive Hauses, plural Häuser)"))
        assert _chip(m, "Article") == "das"
        assert _chip(m, "Genitive") == "Hauses"
        assert _chip(m, "Plural") == "Häuser"

    def test_verb_principal_parts(self):
        m = BUILDERS["de"](_entry("verb", [
            ("sprach", ["past"]),
            ("gesprochen", ["participle", "past"]),
            ("haben", ["auxiliary"]),
        ]))
        assert _chip(m, "Präteritum") == "sprach"
        assert _chip(m, "Partizip II") == "gesprochen"
        assert _chip(m, "Auxiliary") == "haben"


class TestArabic:
    def test_verb_form_masdar_and_charts(self):
        forms = [
            ("كَتَبَ", ["canonical", "form-i"]),
            ("يَكْتُبُ", ["non-past"]),
            ("كِتَابَة", ["noun-from-verb"]),
            ("كَاتِب", ["active", "participle"]),
        ]
        base = ["active", "indicative", "past", "perfective"]
        for p, g, n in (("first-person", "masculine", "singular"),
                        ("second-person", "masculine", "singular"),
                        ("second-person", "feminine", "singular"),
                        ("third-person", "masculine", "singular"),
                        ("third-person", "feminine", "singular")):
            forms.append((f"كتب-{p}-{g}-{n}", base + [p, g, n]))
        m = BUILDERS["ar"](_entry("verb", forms))
        assert _chip(m, "Verb form") == "Form I"
        assert _chip(m, "Maṣdar") == "كِتَابَة"
        assert len(_chart(m, "Past (الماضي)")["rows"]) == 5

    def test_noun_broken_plural(self):
        m = BUILDERS["ar"](_entry("noun", [
            ("كِتَاب", ["canonical", "masculine"]),
            ("كُتُب", ["plural"]),
        ]))
        assert _chip(m, "Gender") == "masculine"
        assert _chip(m, "Plural") == "كُتُب"


class TestSwahili:
    def test_noun_class_and_plural(self):
        m = BUILDERS["sw"](_entry("noun", [
            ("vitabu", ["class-viii", "plural"]),
        ]))
        assert _chip(m, "Plural") == "vitabu"
        assert _chip(m, "Class") == "VIII"


class TestEmpty:
    def test_no_usable_forms_returns_none(self):
        assert BUILDERS["ru"](_entry("verb", [])) is None
        assert BUILDERS["es"](_entry("noun", [("x", ["romanization"])])) is None


class TestStripNominalChips:
    """A word's chosen POS vetoes gender/number chips inherited from a
    homographic noun sense (de/para/no showing 'Plural des')."""

    def _morph(self):
        return {"pos": "noun", "lemma": "de",
                "chips": [{"label": "Gender", "value": "feminine"},
                          {"label": "Plural", "value": "des"}]}

    def test_preposition_loses_gender_and_plural(self):
        out = strip_nominal_chips(self._morph(), "prep")
        assert out.get("chips") in (None, [])
        assert out["lemma"] == "de"

    def test_noun_keeps_its_chips(self):
        out = strip_nominal_chips(self._morph(), "noun")
        assert _chip(out, "Gender") == "feminine"
        assert _chip(out, "Plural") == "des"

    def test_verb_conjugation_chips_survive(self):
        m = {"chips": [{"label": "Gerund", "value": "yendo"},
                       {"label": "Plural", "value": "xs"}]}
        out = strip_nominal_chips(m, "verb")
        assert _chip(out, "Gerund") == "yendo"
        assert _chip(out, "Plural") is None

    def test_none_and_empty_are_safe(self):
        assert strip_nominal_chips(None, "prep") is None
        assert strip_nominal_chips({}, "prep") == {}


class TestHeadwordGenderMarker:
    """The gender letter must come from the HEADWORD, not from feminine
    equivalents / diminutives listed inside parentheses (beta report:
    'il cane' labeled feminine because its expansion mentions canìna f)."""

    def test_marker_outside_parens_wins(self):
        from backend.services.seeder.morphology_charts import _headword_gender_marker
        exp = ("cane m (plural cani, feminine cagna, diminutive canìno m "
               "or canìna f or cagnétta f)")
        assert _headword_gender_marker(exp) == "m"

    def test_greek_romanization_paren_is_skipped(self):
        from backend.services.seeder.morphology_charts import _headword_gender_marker
        assert _headword_gender_marker("σκύλος • (skýlos) m (plural σκύλοι)") == "m"

    def test_german_neuter_diminutive_does_not_leak(self):
        from backend.services.seeder.morphology_charts import _headword_gender_marker
        exp = "Becher m (strong, genitive Bechers, plural Becher, diminutive Becherchen n)"
        assert _headword_gender_marker(exp) == "m"

    def test_common_gender_returns_none(self):
        from backend.services.seeder.morphology_charts import _headword_gender_marker
        assert _headword_gender_marker("artista m or f (plural artisti)") is None

    def test_no_marker_returns_none(self):
        from backend.services.seeder.morphology_charts import _headword_gender_marker
        assert _headword_gender_marker("correr (first-person singular presente corro)") is None


class TestPortugueseDerivedTenses:
    """The owner caught futuro do subjuntivo missing from every expanded
    chart while the Gym drilled it. The raw kaikki dump isn't shipped, so
    the three mechanically-safe tenses are derived from data the file
    already holds — and this pins the SHIPPED data file, not just the code.
    """

    @classmethod
    def setup_class(cls):
        import json
        from pathlib import Path
        path = Path(__file__).resolve().parents[2] / "data" / "pt_morphology.json"
        cls.data = json.loads(path.read_text(encoding="utf-8"))

    def _chart(self, word, title):
        return next((c for c in self.data[word]["charts"]
                     if c["title"] == title), None)

    def test_future_subjunctive_shipped_for_regulars_and_irregulars(self):
        # Regular -ar: quando eu falar / nós falarmos
        rows = self._chart("falar", "Subjunctive (future)")["rows"]
        assert rows[0][1] == "falar" and rows[3][1] == "falarmos"
        # Irregular stems come from the preterite, not the lemma.
        assert self._chart("ter", "Subjunctive (future)")["rows"][0][1] == "tiver"
        assert self._chart("ser", "Subjunctive (future)")["rows"][3][1] == "formos"
        assert self._chart("fazer", "Subjunctive (future)")["rows"][0][1] == "fizer"

    def test_conditional_uses_the_contracted_stems(self):
        assert self._chart("falar", "Conditional")["rows"][0][1] == "falaria"
        assert self._chart("fazer", "Conditional")["rows"][0][1] == "faria"
        assert self._chart("dizer", "Conditional")["rows"][0][1] == "diria"
        # And the accent-carrying plural endings.
        assert self._chart("falar", "Conditional")["rows"][3][1] == "falaríamos"

    def test_personal_infinitive_builds_on_the_lemma(self):
        rows = self._chart("fazer", "Personal infinitive")["rows"]
        assert rows[1][1] == "fazeres" and rows[3][1] == "fazermos"

    def test_por_is_left_underived_rather_than_wrong(self):
        # pôr contracts irregularly (pusermos, poríamos) — no chart is
        # better than a wrong one, so the -ar/-er/-ir guard excludes it.
        titles = [c["title"] for c in self.data["pôr"]["charts"]]
        assert "Conditional" not in titles
        assert "Personal infinitive" not in titles

    def test_augment_is_idempotent(self):
        import copy

        from backend.services.seeder.morphology_charts import augment_pt_entry
        entry = copy.deepcopy(self.data["falar"])
        assert augment_pt_entry("falar", entry) is False  # already there


class TestSpanishItalianCatalanDerivedTenses:
    """Same class of gap as the PT one, in three more languages: the Gym
    offers the conditional (and, in es, the imperfect subjunctive) while the
    shipped charts stopped short. Both derive mechanically — the conditional
    stem IS the future stem, and the es imperfect subjunctive stem is the
    3pl preterite minus -ron. Pins the SHIPPED files."""

    @classmethod
    def setup_class(cls):
        import json
        from pathlib import Path
        data_dir = Path(__file__).resolve().parents[2] / "data"
        cls.data = {
            code: json.loads(
                (data_dir / f"{code}_morphology.json").read_text(encoding="utf-8")
            )
            for code in ("es", "it", "ca")
        }

    def _chart(self, code, word, title):
        return next((c for c in self.data[code][word]["charts"]
                     if c["title"] == title), None)

    def test_spanish_conditional_carries_irregular_future_stems(self):
        assert self._chart("es", "hablar", "Conditional")["rows"][0][1] == "hablaría"
        assert self._chart("es", "tener", "Conditional")["rows"][0][1] == "tendría"
        assert self._chart("es", "hacer", "Conditional")["rows"][0][1] == "haría"

    def test_spanish_imperfect_subjunctive_stems_and_nosotros_accent(self):
        rows = self._chart("es", "hablar", "Subjunctive (imperfect)")["rows"]
        assert rows[0][1] == "hablara" and rows[3][1] == "habláramos"
        # Irregular stems ride along from the preterite.
        assert self._chart("es", "ser", "Subjunctive (imperfect)")["rows"][0][1] == "fuera"
        assert self._chart("es", "decir", "Subjunctive (imperfect)")["rows"][3][1] == "dijéramos"

    def test_italian_conditional_keeps_the_stress_mark_convention(self):
        # The shipped it charts mark stress (parlerànno) — the derived rows
        # match that style rather than mixing plain orthography in.
        assert self._chart("it", "parlare", "Conditional")["rows"][0][1] == "parlerèi"
        assert self._chart("it", "andare", "Conditional")["rows"][0][1] == "andrèi"
        assert self._chart("it", "essere", "Conditional")["rows"][2][1] == "sarèbbe"

    def test_catalan_conditional_carries_irregular_future_stems(self):
        assert self._chart("ca", "parlar", "Conditional")["rows"][0][1] == "parlaria"
        assert self._chart("ca", "anar", "Conditional")["rows"][0][1] == "aniria"
        assert self._chart("ca", "tenir", "Conditional")["rows"][3][1] == "tindríem"

    def test_augment_is_idempotent(self):
        import copy

        from backend.services.seeder.morphology_charts import augment_romance_entry
        entry = copy.deepcopy(self.data["es"]["hablar"])
        assert augment_romance_entry("es", "hablar", entry) is False
