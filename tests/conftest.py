import pytest
from sse_starlette.sse import AppStatus


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def reset_appstatus_event():
    # https://github.com/sysid/sse-starlette/issues/59
    AppStatus.should_exit_event = None
