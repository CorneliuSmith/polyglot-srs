"""`/api/health` names what it is running.

The trap this closes: "is the build with X deployed yet?" had no answer
that wasn't a guess, because health returned `{"status": "ok"}` and
nothing else. Every fact here degrades to null rather than a made-up
value — a health endpoint that invents a commit is worse than one that
says it doesn't know.
"""
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import create_app
from backend.services import build_info as bi


def test_health_carries_a_build_stamp():
    bi.build_info.cache_clear()
    with TestClient(create_app()) as client:
        body = client.get("/api/health").json()
    assert body["status"] == "ok"
    build = body["build"]
    assert set(build) >= {"sha", "built_at", "latest_migration", "migrations_shipped"}
    # From a checkout the migration facts are real, whatever the platform
    # did or didn't pass in.
    assert build["migrations_shipped"] > 100
    assert build["latest_migration"].endswith(".sql")


def test_latest_migration_is_the_newest_by_filename(tmp_path: Path):
    for name in ("20260102000000_b.sql", "20260101000000_a.sql", "notes.md"):
        (tmp_path / name).write_text("", encoding="utf-8")
    assert bi._latest_migration(tmp_path) == "20260102000000_b.sql"
    assert bi._migrations_shipped(tmp_path) == 2


def test_no_migrations_dir_is_null_not_an_error(tmp_path: Path):
    """An image built without the migration files must still answer — and
    answer with the zero that says the schema check is blind."""
    missing = tmp_path / "nowhere"
    assert bi._latest_migration(missing) is None
    assert bi._migrations_shipped(missing) == 0


def test_sha_prefers_the_platform_build_arg(monkeypatch):
    monkeypatch.setenv("BUILD_SHA", "abc123")
    assert bi._sha_from_env() == "abc123"
    monkeypatch.setenv("BUILD_SHA", "   ")
    monkeypatch.delenv("SOURCE_COMMIT", raising=False)
    monkeypatch.delenv("RENDER_GIT_COMMIT", raising=False)
    monkeypatch.delenv("GIT_SHA", raising=False)
    assert bi._sha_from_env() is None
