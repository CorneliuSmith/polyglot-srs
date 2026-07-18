"""Computed script→Latin readings for example sentences (grammar path)."""

from backend.services.readings import sentence_reading


class TestSentenceReading:
    def test_hindi_romanizes(self):
        r = sentence_reading("मैं घर जा रहा हूँ।", "hi")
        assert r and "ghar" in r

    def test_russian_romanizes(self):
        r = sentence_reading("Мой дом — твой дом.", "ru")
        assert r and r.lower().startswith("moj")

    def test_latin_language_gets_no_reading(self):
        assert sentence_reading("Yo voy a casa.", "es") is None

    def test_arabic_deliberately_unsupported(self):
        # unvocalized Arabic would need short vowels a romanization lacks
        assert sentence_reading("أنا ذاهب إلى البيت.", "ar") is None

    def test_empty_and_none_safe(self):
        assert sentence_reading("", "ru") is None
        assert sentence_reading(None, "hi") is None
        assert sentence_reading("   ", "hi") is None
