import pytest

from runtime_context import RuntimeContextWrapper


@pytest.fixture(autouse=True)
def rc():
    return RuntimeContextWrapper()
