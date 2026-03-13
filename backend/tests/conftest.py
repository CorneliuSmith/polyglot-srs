import pytest
import random


@pytest.fixture(autouse=False)
def fixed_seed():
    random.seed(42)
    yield
    random.seed()
