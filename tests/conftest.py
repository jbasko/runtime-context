import pytest

from runtime_context import RuntimeContext


@pytest.fixture(autouse=True)
def rc():
    runtime_context = RuntimeContext()
    ctx = runtime_context()
    with ctx:
        yield runtime_context
