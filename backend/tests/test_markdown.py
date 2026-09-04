"""Card markdown on the way in (services/markdown.py)."""
from __future__ import annotations

from backend.services.markdown import clean_markdown


class TestCleanMarkdown:
    def test_markdown_itself_is_untouched(self):
        text = "**Ser** is for identity.\n\n- ser: soy, eres\n- estar: estoy\n\n| a | b |\n|---|---|\n| 1 | 2 |"
        assert clean_markdown(text) == text

    def test_raw_html_tags_are_removed_text_kept(self):
        assert clean_markdown("Use <b>ser</b> here<script>alert(1)</script>.") == \
            "Use ser herealert(1)."

    def test_unsafe_link_destinations_are_dropped(self):
        assert clean_markdown("See [this](javascript:alert(1)) and [that](https://x.org/a).") == \
            "See this and [that](https://x.org/a)."
        assert clean_markdown("![pic](data:image/png;base64,AAAA)") == "pic"

    def test_relative_and_fragment_links_survive(self):
        assert clean_markdown("[a](#top) [b](/path) [c](./rel)") == "[a](#top) [b](/path) [c](./rel)"

    def test_a_less_than_in_prose_is_not_a_tag(self):
        assert clean_markdown("a < b and b > c") == "a < b and b > c"

    def test_none_and_empty_pass_through(self):
        assert clean_markdown(None) is None
        assert clean_markdown("") == ""
