import pytest

def pytest_collection_modifyitems(items):
    for item in items:
        if "asyncio" in item.keywords:
            item.add_marker(pytest.mark.anyio)

@pytest.fixture
def anyio_backend():
    return "asyncio"
