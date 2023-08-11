# flake8: noqa
import asyncio
import time

import pytest

from horoscoper.api.batcher import ContextBatcher
from horoscoper.horoscope import LLMContext


class FakeInfer:
    def __init__(self):
        self.enqueued = []

    def enqueue(self, contexts: list[LLMContext]):
        self.enqueued.append(contexts)

    async def enqueue_async(self, contexts: list[LLMContext]):
        self.enqueue(contexts)


@pytest.fixture
def fake_infer(monkeypatch):
    fake_infer = FakeInfer()
    monkeypatch.setattr("horoscoper.api.batcher.infer", fake_infer)
    return fake_infer


@pytest.mark.anyio
async def test_batcher_asap_enqueue(fake_infer: FakeInfer):
    batch_size = 4
    window_size = 1000

    contexts = [LLMContext() for _ in range(batch_size)]
    async with ContextBatcher(
        batch_size=batch_size, window_size_ms=window_size
    ) as batcher:
        for context in contexts:
            await batcher.add_context_to_batch(context)

        # Give a loop chance to advance
        await asyncio.sleep(0)

        assert (
            fake_infer.enqueued[0] == contexts
        ), "Contexts are enqueued ASAP if batch size is reached"


@pytest.mark.anyio
async def test_batcher_wait_for_window(fake_infer: FakeInfer):
    batch_size = 4
    window_size = 50

    contexts = [LLMContext() for _ in range(batch_size // 2)]
    async with ContextBatcher(
        batch_size=batch_size, window_size_ms=window_size
    ) as batcher:
        for context in contexts:
            await batcher.add_context_to_batch(context)
        assert (
            len(fake_infer.enqueued) == 0
        ), "Nothing is enqueued before the batch window is over"

        # Wait until window expires
        await asyncio.sleep(window_size / 1000 + 0.01)
        assert (
            fake_infer.enqueued[0] == contexts[:2]
        ), "Contexts are enqueued after the batch window is over"


@pytest.mark.anyio
async def test_batcher_stale_contexts(fake_infer: FakeInfer, monkeypatch):
    batch_size = 4
    window_size = 25

    contexts = [LLMContext() for _ in range(batch_size // 2)]

    async with ContextBatcher(
        batch_size=batch_size, window_size_ms=window_size
    ) as batcher:
        now = time.monotonic()

        with monkeypatch.context() as m:
            m.setattr("time.monotonic", lambda: now - 10)
            for context in contexts:
                await batcher.add_context_to_batch(context)

        await asyncio.sleep(0)
        assert (
            fake_infer.enqueued[0] == contexts
        ), "Stale contexts are enqueued asap even if batch size is not reached"


@pytest.mark.anyio
async def test_batcher_long_run(fake_infer: FakeInfer):
    batch_size = 4
    window_size = 50

    contexts = [LLMContext() for _ in range(batch_size * 2)]

    async with ContextBatcher(
        batch_size=batch_size, window_size_ms=window_size
    ) as batcher:
        for context in contexts[:2]:
            await batcher.add_context_to_batch(context)

        await asyncio.sleep(window_size / 1000 + 0.01)
        assert (
            fake_infer.enqueued[0] == contexts[:2]
        ), "First two elements enqueued after window expired"

        for context in contexts[2:]:
            await batcher.add_context_to_batch(context)

        await asyncio.sleep(0)
        assert (
            fake_infer.enqueued[1] == contexts[2:6]
        ), "Next 4 as soon as batch is filled"

        await asyncio.sleep(window_size / 1000 + 0.01)
        assert (
            fake_infer.enqueued[2] == contexts[6:]
        ), "Last 2 after next window expiration"
