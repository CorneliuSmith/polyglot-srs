import random

import pytest

from backend.services.rate_limit import (
    ai_review_limiter,
    stt_limiter,
    tts_limiter,
    tutor_chat_limiter,
)


def _wordnet_present() -> bool:
    """Is the WordNet corpus on this machine?

    The English seeder builds its definitions from WordNet, which is data
    rather than code: `pip install nltk` does not bring it, and the seeder
    fetches it on first use. That download is the only network call anywhere
    in the test suite's dependencies, and when nltk's data host has a bad
    afternoon it takes thirteen tests down in a way that reads exactly like a
    code regression — CI failed three separate jobs this way in one pull
    request, on a docs-only diff.

    So the corpus gets the same treatment camel-tools and the spaCy models
    already get: absent means SKIP, not FAIL. A missing corpus is an
    environment fact. Real breakage in the seeder still fails, because with
    the corpus present nothing here is skipped.
    """
    # Ask the reader the seeder uses, not nltk.data.find. find() misses a
    # corpus that is present as corpora/wordnet.zip without an unpacked
    # directory beside it, which is how `nltk.download('wordnet')` leaves it
    # on macOS — so every one of these tests skipped on a machine where
    # wn.synsets('book') returns fifteen results.
    try:
        from nltk.corpus import wordnet as wn

        return bool(wn.synsets("book"))
    except LookupError:
        return False
    except Exception:  # noqa: BLE001 — a broken data dir is still "absent"
        return False


requires_wordnet = pytest.mark.skipif(
    not _wordnet_present(),
    reason="NLTK WordNet corpus not installed (data download, not code)",
)


@pytest.fixture(autouse=False)
def fixed_seed():
    random.seed(42)
    yield
    random.seed()


@pytest.fixture(autouse=True)
def _reset_rate_limiters():
    """Keep the AI rate limiters from leaking across tests.

    Every limiter belongs here, without exception. tts_limiter was
    missing from this list, which cost three tests that
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
    stt_limiter.reset()
    yield
