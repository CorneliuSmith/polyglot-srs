"""
NLP backend registry.

Provides get_nlp, init_nlp_backends, validate_answer_async, and NLP_BACKENDS.
Full async convenience and graceful backend loading are implemented here;
each concrete backend (Russian, Arabic, English) is lazily imported so that
missing libraries produce a warning rather than crashing the app.
"""
from __future__ import annotations

import asyncio
import logging

from backend.services.nlp.base import AnswerResult, BaseNLP

logger = logging.getLogger(__name__)

# Module-level registry: language_code -> BaseNLP instance
NLP_BACKENDS: dict[str, BaseNLP] = {}


def init_nlp_backends() -> None:
    """Instantiate and register all available NLP backends.

    Each backend is wrapped in try/except so that missing libraries (not yet
    installed) emit a warning rather than crashing the app.  This allows
    incremental backend development — the server can start with 0 backends
    and serve languages as their dependencies are installed.
    """
    candidates = [
        ("ru", "backend.services.nlp.russian", "RussianNLP"),
        ("ar", "backend.services.nlp.arabic", "ArabicNLP"),
        ("en", "backend.services.nlp.english", "EnglishNLP"),
        ("sw", "backend.services.nlp.swahili", "SwahiliNLP"),
        ("tr", "backend.services.nlp.turkish", "TurkishNLP"),
        ("yo", "backend.services.nlp.yoruba", "YorubaNLP"),
        ("ha", "backend.services.nlp.hausa", "HausaNLP"),
        ("xh", "backend.services.nlp.xhosa", "XhosaNLP"),
    ]
    for lang_code, module_path, class_name in candidates:
        try:
            import importlib
            module = importlib.import_module(module_path)
            cls = getattr(module, class_name)
            NLP_BACKENDS[lang_code] = cls()
            logger.info("Registered NLP backend: %s (%s)", lang_code, class_name)
        except ImportError as exc:
            logger.warning(
                "NLP backend for '%s' unavailable (missing library): %s",
                lang_code,
                exc,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "NLP backend for '%s' failed to initialize: %s",
                lang_code,
                exc,
            )


def get_nlp(language_code: str) -> BaseNLP:
    """Retrieve a registered NLP backend by language code.

    Args:
        language_code: ISO 639-1 language code (e.g. "en", "ru", "ar").

    Returns:
        The registered BaseNLP instance.

    Raises:
        ValueError: If no backend is registered for *language_code*.
    """
    if language_code not in NLP_BACKENDS:
        raise ValueError(
            f"No NLP backend registered for language code '{language_code}'. "
            f"Available backends: {list(NLP_BACKENDS.keys())}"
        )
    return NLP_BACKENDS[language_code]


async def validate_answer_async(
    language_code: str,
    user_input: str,
    correct_answer: str,
    card_context: dict | None = None,
) -> tuple[AnswerResult, str | None]:
    """Async convenience wrapper around BaseNLP.check_answer.

    Runs the synchronous check_answer in a thread pool via asyncio.to_thread
    so it does not block the event loop.

    Args:
        language_code: ISO 639-1 code identifying the NLP backend to use.
        user_input: The learner's typed answer.
        correct_answer: The expected answer for the card.
        card_context: Optional card metadata dict.

    Returns:
        Tuple of (AnswerResult, optional feedback message).

    Raises:
        ValueError: If no backend is registered for *language_code*.
    """
    nlp = get_nlp(language_code)
    return await asyncio.to_thread(
        nlp.check_answer, user_input, correct_answer, card_context
    )
