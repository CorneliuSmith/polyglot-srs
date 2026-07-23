"""Unit tests for the optional Apertium morphology client (WP42). No network:
the parser is pure, and analyze_lemmas is exercised against a fake AsyncClient."""
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from backend.services import apertium


def _settings(url="http://apy.test"):
    return SimpleNamespace(apertium_api_url=url)


# ── analysis-string parsing (pure) ──────────────────────────────────────────


@pytest.mark.parametrize(
    "analysis,expected",
    [
        ("corre/correr<vblex><pri><p3><sg>", {"correr"}),
        ("casa/casa<n><f><sg>/casar<vblex><inf>", {"casa", "casar"}),
        ("Gatos/gato<n><m><pl>", {"gato"}),
        ("xyz/*xyz", set()),          # unknown token -> no valid reading
        ("Kwa", set()),                # no analysis at all
        ("", set()),
    ],
)
def test_lemmas_from_analysis(analysis, expected):
    assert apertium._lemmas_from_analysis(analysis) == expected


# ── availability gate ───────────────────────────────────────────────────────


def test_available_needs_url_and_supported_language():
    with patch("backend.services.apertium.get_settings", return_value=_settings()):
        assert apertium.apertium_available("sw") is True
        assert apertium.apertium_available("zz") is False   # unmapped language
    with patch("backend.services.apertium.get_settings", return_value=_settings("")):
        assert apertium.apertium_available("sw") is False   # no URL configured


def test_available_survives_unconfigured_settings():
    # get_settings() raising (no env) must not blow up the checker.
    with patch("backend.services.apertium.get_settings", side_effect=RuntimeError):
        assert apertium.apertium_available("sw") is False


# ── analyze_lemmas against a fake APy ────────────────────────────────────────


class _FakeResp:
    def __init__(self, data):
        self._data = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._data


class _FakeClient:
    def __init__(self, data):
        self._data = data

    async def __aenter__(self):
        return self

    async def __aexit__(self, *a):
        return False

    async def get(self, url, params=None):
        return _FakeResp(self._data)


async def test_analyze_lemmas_collects_all_readings():
    payload = [
        ["Mbwa/mbwa<n>", "Mbwa"],
        ["anakimbia/kimbia<vblex><pres>", "anakimbia"],
    ]
    with patch("backend.services.apertium.get_settings", return_value=_settings()), \
         patch("backend.services.apertium.httpx.AsyncClient",
               lambda **kw: _FakeClient(payload)):
        lemmas = await apertium.analyze_lemmas("sw", "Mbwa anakimbia.")
    assert lemmas == {"mbwa", "kimbia"}


async def test_analyze_lemmas_empty_when_not_configured():
    with patch("backend.services.apertium.get_settings", return_value=_settings("")):
        assert await apertium.analyze_lemmas("sw", "anything") == set()


async def test_analyze_lemmas_swallows_http_errors():
    def _boom(**kw):
        raise RuntimeError("network down")

    with patch("backend.services.apertium.get_settings", return_value=_settings()), \
         patch("backend.services.apertium.httpx.AsyncClient", _boom):
        assert await apertium.analyze_lemmas("sw", "anything") == set()
