import random

import pytest

from backend.services.rate_limit import (
    ai_review_limiter,
    tts_limiter,
    tutor_chat_limiter,
)


@pytest.fixture(autouse=False)
def fixed_seed():
    random.seed(42)
    yield
    random.seed()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Keep the AI rate limiters from leaking across tests.

    tts_limiter was missing from this list, which cost three tests that
    were filed in CLAUDE.md as needing a live provider. They don't: the
    TTS cap is 30 calls a minute per user, every test in test_audio.py
    uses the same user id, and the documented way to run the full suite
    sets REDIS_URL — so the budget lived in Redis and survived from one
    test to the next until the later ones got 429s. Alone, or without
    REDIS_URL, they passed, which is exactly what "environmental" looks
    like from the outside.
    """
    tutor_chat_limiter.reset()
    ai_review_limiter.reset()
    tts_limiter.reset()
    yield
