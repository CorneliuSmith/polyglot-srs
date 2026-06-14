import random

import pytest

from backend.services.rate_limit import ai_review_limiter, tutor_chat_limiter


@pytest.fixture(autouse=False)
def fixed_seed():
    random.seed(42)
    yield
    random.seed()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Keep the in-memory AI rate limiters from leaking across tests."""
    tutor_chat_limiter.reset()
    ai_review_limiter.reset()
    yield
