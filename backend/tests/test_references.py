"""Tests for reference-link sanitization."""
from backend.services.references import (
    MAX_REFERENCES,
    MAX_RELATED,
    clean_references,
    clean_related,
    reference_key,
)
from backend.services.srs_stages import stage_for


class TestCleanReferences:
    def test_keeps_valid_http_links(self):
        refs = [
            {"title": "Wiktionary", "url": "https://en.wiktionary.org/wiki/-de"},
            {"title": "Wikipedia", "url": "http://example.org/x"},
        ]
        assert clean_references(refs) == refs

    def test_rejects_non_http_schemes(self):
        refs = [
            {"title": "evil", "url": "javascript:alert(1)"},
            {"title": "data", "url": "data:text/html,x"},
            {"title": "file", "url": "file:///etc/passwd"},
        ]
        assert clean_references(refs) == []

    def test_drops_missing_title_or_url(self):
        refs = [
            {"title": "", "url": "https://ok.com"},
            {"title": "no url", "url": ""},
            {"url": "https://only-url.com"},
        ]
        assert clean_references(refs) == []

    def test_caps_count(self):
        refs = [{"title": f"t{i}", "url": f"https://x{i}.com"} for i in range(50)]
        assert len(clean_references(refs)) == MAX_REFERENCES

    def test_non_list_returns_empty(self):
        assert clean_references(None) == []
        assert clean_references("nope") == []
        assert clean_references([{"junk": 1}, "x", 5]) == []

    def test_truncates_long_fields(self):
        out = clean_references([{"title": "t" * 500, "url": "https://" + "a" * 1000}])
        assert len(out[0]["title"]) <= 200
        assert len(out[0]["url"]) <= 500

    def test_keeps_offline_book_entries(self):
        refs = [
            {"title": "Ser and estar", "book": "Butt & Benjamin", "page": "29"},
            {"title": "No page", "book": "Some Grammar"},
        ]
        out = clean_references(refs)
        assert out[0] == {"title": "Ser and estar", "book": "Butt & Benjamin", "page": "29"}
        assert out[1] == {"title": "No page", "book": "Some Grammar"}

    def test_book_entry_without_title_or_source_dropped(self):
        assert clean_references([{"book": "Orphan Book"}]) == []
        assert clean_references([{"title": "no url no book"}]) == []

    def test_url_wins_over_book_when_both_given(self):
        out = clean_references(
            [{"title": "Both", "url": "https://x.com", "book": "B"}]
        )
        assert out == [{"title": "Both", "url": "https://x.com"}]

    def test_reference_key_prefers_url(self):
        assert reference_key({"title": "T", "url": "https://x.com"}) == "https://x.com"
        assert reference_key({"title": "T", "book": "B"}) == "T"


class TestCleanRelated:
    def test_keeps_title_and_contrast(self):
        entries = [{"title": "Accusative", "contrast": "Marks the object."}]
        assert clean_related(entries) == entries

    def test_contrast_optional(self):
        assert clean_related([{"title": "Accusative"}]) == [{"title": "Accusative"}]

    def test_drops_untitled_and_junk(self):
        assert clean_related([{"contrast": "no title"}, "x", 5, None]) == []
        assert clean_related("nope") == []

    def test_caps_count_and_lengths(self):
        entries = [{"title": f"t{i}", "contrast": "c" * 500} for i in range(20)]
        out = clean_related(entries)
        assert len(out) == MAX_RELATED
        assert all(len(e["contrast"]) <= 200 for e in out)


class TestStageFor:
    def test_stability_bands(self):
        assert stage_for("grammar", "review", 0) == "beginner"
        assert stage_for("grammar", "review", 7) == "adept"
        assert stage_for("grammar", "review", 45) == "seasoned"
        assert stage_for("grammar", "review", 100) == "expert"
        assert stage_for("grammar", "review", 400) == "master"

    def test_relearning_is_ghost_regardless_of_stability(self):
        assert stage_for("grammar", "relearning", 400) == "ghost"

    def test_personal_is_self_study(self):
        assert stage_for("personal", "review", 400) == "self_study"

    def test_none_stability_is_beginner(self):
        assert stage_for("vocabulary", "new", None) == "beginner"
