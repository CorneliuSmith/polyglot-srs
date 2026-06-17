"""Tests for drill-answerability validation (shared by contributor + generator)."""

import pytest

from backend.services.drills import has_blank, is_answerable, validate_drill
from backend.services.nlp import init_nlp_backends


@pytest.fixture(scope="module", autouse=True)
def _nlp():
    init_nlp_backends()


class TestHasBlank:
    def test_present(self):
        assert has_blank("Kitap {{answer}}.")

    def test_absent(self):
        assert not has_blank("Kitap masada.")
        assert not has_blank("")
        assert not has_blank(None)


class TestIsAnswerable:
    @pytest.mark.asyncio
    async def test_turkish_answer_validates(self):
        assert await is_answerable("tr", "masada") is True

    @pytest.mark.asyncio
    async def test_empty_answer(self):
        assert await is_answerable("tr", "  ") is False

    @pytest.mark.asyncio
    async def test_unknown_language(self):
        assert await is_answerable("zz", "x") is False


class TestValidateDrill:
    @pytest.mark.asyncio
    async def test_valid(self):
        assert await validate_drill("tr", "Kitap {{answer}}.", "masada") is True

    @pytest.mark.asyncio
    async def test_no_blank(self):
        assert await validate_drill("tr", "Kitap masada.", "masada") is False

    @pytest.mark.asyncio
    async def test_empty_answer(self):
        assert await validate_drill("tr", "Kitap {{answer}}.", "") is False
