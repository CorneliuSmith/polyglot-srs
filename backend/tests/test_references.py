"""Tests for reference-link sanitization."""
from backend.services.references import MAX_REFERENCES, clean_references


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
