from contextlib import contextmanager
from unittest.mock import AsyncMock

import pytest
from fakeredis.aioredis import FakeRedis
from httpx import AsyncClient

from horoscoper.api.main import app
from horoscoper.api.state import AppState, get_app_state
from horoscoper.api.views import APIInferRequest
from horoscoper.tasks.infer import InferMessage, InferMessageStatus


@pytest.fixture
def fake_async_redis():
    yield FakeRedis()


@pytest.fixture
async def client(fake_async_redis):
    class FakeState(AppState):
        def __init__(self, *args, **kwargs):
            self.redis = fake_async_redis
            self.batcher = AsyncMock()

    app_state = FakeState()
    app.dependency_overrides[get_app_state] = lambda: app_state

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


class FakePubSub:
    def __init__(self, messages: list[dict]):
        self.messages = messages
        self.i = 0

    async def get_message(self, *args, **kwargs):
        if self.i >= len(self.messages):
            raise RuntimeError("Trying to get messages from a closed PubSub")
        msg = self.messages[self.i]
        self.i += 1
        return msg

    async def subscribe(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        pass


@contextmanager
def fake_pubsub_messages(fake_async_redis, messages: list[dict]):
    fake_pub_sub = FakePubSub(messages=messages)
    old_pub_sub = fake_async_redis.pubsub
    try:
        fake_async_redis.pubsub = fake_pub_sub
        yield
    finally:
        fake_async_redis.pubsub = old_pub_sub


@pytest.mark.anyio
async def test_healthcheck(client):
    response = await client.get("/healthcheck")
    assert response.status_code == 200


@pytest.mark.anyio
async def test_infer_sse(client, monkeypatch, fake_async_redis):
    """
    This test covers logic inside stream response without redis and queue.
    """
    infer_messages = [
        InferMessage(status=InferMessageStatus.IN_PROGRESS, text="Hello "),
        InferMessage(status=InferMessageStatus.IN_PROGRESS, text="World"),
        InferMessage(status=InferMessageStatus.FINISHED, text="!"),
    ]

    pubsub_messages = [
        {"type": "subscribe", "data": 1},
        *[
            {"type": "message", "data": im.model_dump_json().encode()}
            for im in infer_messages
        ],
    ]

    with fake_pubsub_messages(fake_async_redis, pubsub_messages):
        request_body = APIInferRequest(text="Hey!").model_dump()

        async with client.stream(
            "POST",
            "/api/v1/infer",
            json=request_body,
        ) as response:
            assert response.status_code == 200

            response_lines = []
            async for line in response.aiter_lines():
                # Separator between messages
                if line != "":
                    response_lines.append(line)

            assert response_lines == [
                f"data: {im.model_dump_json()}" for im in infer_messages
            ]


@pytest.mark.anyio
async def test_infer_sse_timeout(client, fake_async_redis):
    pubsub_messages = [{"type": "subscribe", "data": ""}, None]

    with fake_pubsub_messages(fake_async_redis, messages=pubsub_messages):
        request_body = APIInferRequest(text="Hey!").model_dump()

        async with client.stream(
            "POST",
            "/api/v1/infer",
            json=request_body,
        ) as response:
            assert response.status_code == 200

            response_lines = []
            async for line in response.aiter_lines():
                # Separator between messages
                if line != "":
                    response_lines.append(line)

            assert len(response_lines) == 1
            assert "error" in response_lines[0]
