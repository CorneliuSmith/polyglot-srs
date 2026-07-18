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
