"""Unit tests for the central task->model registry (WP39). Pure resolution
logic — no API key or DB needed (get_settings is patched)."""
from types import SimpleNamespace
from unittest.mock import patch

from backend.services.models import LOW_RESOURCE_LANGUAGES, TASK_MODELS, resolve_model


def _settings(**over):
    base = {
        "tutor_model": "sonnet",
        "tutor_model_low_resource": "opus",
        "tutor_summary_model": "summary",
    }
    base.update(over)
    return SimpleNamespace(**base)


def test_each_task_resolves_to_its_configured_model():
    with patch("backend.services.models.get_settings", return_value=_settings()):
        assert resolve_model("tutor_chat") == "sonnet"
        assert resolve_model("reader") == "sonnet"
        assert resolve_model("tutor_summary") == "summary"
        assert resolve_model("semantic_check") == "summary"
        assert resolve_model("translate") == "summary"
        assert resolve_model("grammar_maker") == "sonnet"
        # checker sits one tier up (§6: never self-certify)
        assert resolve_model("grammar_checker") == "opus"
        assert resolve_model("sentence_maker") == "sonnet"
        assert resolve_model("sentence_checker") == "opus"


def test_explicit_override_wins():
    with patch("backend.services.models.get_settings", return_value=_settings()):
        assert resolve_model("tutor_chat", "es", override="custom-model") == "custom-model"


def test_low_resource_pins_chat_reader_and_makers_only():
    with patch("backend.services.models.get_settings", return_value=_settings()):
        for lang in LOW_RESOURCE_LANGUAGES:
            assert resolve_model("tutor_chat", lang) == "opus"
            assert resolve_model("reader", lang) == "opus"
            assert resolve_model("grammar_maker", lang) == "opus"
            assert resolve_model("sentence_maker", lang) == "opus"
            # summary / translate are NOT pinned by language
            assert resolve_model("tutor_summary", lang) == "summary"
            assert resolve_model("translate", lang) == "summary"
        # high-resource languages are unaffected
        assert resolve_model("tutor_chat", "es") == "sonnet"
        assert resolve_model("grammar_maker", "fr") == "sonnet"


def test_unknown_task_falls_back_to_chat_model():
    with patch("backend.services.models.get_settings", return_value=_settings()):
        assert resolve_model("nope") == "sonnet"


def test_registry_covers_the_generation_tasks():
    # the Part C/D seam: maker + checker for both content types are named here.
    for t in ("grammar_maker", "grammar_checker", "sentence_maker", "sentence_checker"):
        assert t in TASK_MODELS
