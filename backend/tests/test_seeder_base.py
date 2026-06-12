"""Tests for BaseSeeder infrastructure."""
import pytest

from backend.services.seeder.base import BaseSeeder

# ── Concrete stub for testing abstract interface ──────────────────────────────

class StubSeeder(BaseSeeder):
    language_code = "xx"

    async def download(self) -> None:
        pass

    async def transform(self) -> list[dict]:
        return []


# ── rank_to_level mapping ─────────────────────────────────────────────────────

class TestRankToLevel:
    def test_none_returns_none(self):
        assert BaseSeeder.rank_to_level(None) is None

    def test_rank_1_is_a1(self):
        assert BaseSeeder.rank_to_level(1) == "A1"

    def test_rank_500_is_a1(self):
        assert BaseSeeder.rank_to_level(500) == "A1"

    def test_rank_501_is_a2(self):
        assert BaseSeeder.rank_to_level(501) == "A2"

    def test_rank_1500_is_a2(self):
        assert BaseSeeder.rank_to_level(1500) == "A2"

    def test_rank_1501_is_b1(self):
        assert BaseSeeder.rank_to_level(1501) == "B1"

    def test_rank_3000_is_b1(self):
        assert BaseSeeder.rank_to_level(3000) == "B1"

    def test_rank_3001_is_b2(self):
        assert BaseSeeder.rank_to_level(3001) == "B2"

    def test_rank_5000_is_b2(self):
        assert BaseSeeder.rank_to_level(5000) == "B2"

    def test_rank_5001_is_c1(self):
        assert BaseSeeder.rank_to_level(5001) == "C1"

    def test_rank_99999_is_c1(self):
        assert BaseSeeder.rank_to_level(99999) == "C1"

    def test_rank_zero_is_a1(self):
        assert BaseSeeder.rank_to_level(0) == "A1"


# ── Abstract interface enforcement ────────────────────────────────────────────

class TestBaseSeederAbstract:
    def test_cannot_instantiate_directly(self):
        with pytest.raises(TypeError):
            BaseSeeder("postgresql://localhost/test")  # type: ignore[abstract]

    def test_stub_can_be_instantiated(self):
        seeder = StubSeeder("postgresql://localhost/test")
        assert seeder.language_code == "xx"

    def test_language_id_starts_none(self):
        seeder = StubSeeder("postgresql://localhost/test")
        assert seeder.language_id is None

    def test_db_url_stored(self):
        url = "postgresql://localhost/test"
        seeder = StubSeeder(url)
        assert seeder.db_url == url
