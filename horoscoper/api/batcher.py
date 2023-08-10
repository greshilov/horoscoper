import asyncio
import contextlib
import logging
import time

import async_timeout

from horoscoper.llm import LLMContext
from horoscoper.tasks import infer
from horoscoper.utils import spawn

logger = logging.getLogger(__name__)
QueueObject = tuple[int, LLMContext]


class ContextBatcher:
    def __init__(self, batch_size: int, window_size_ms: int):
        self._queue: asyncio.Queue[QueueObject] = asyncio.Queue()
        self._is_running = False
        self._background_task = None
        self._batch_size = batch_size
        self._window_size = window_size_ms / 1000

    async def _fill_batch(self) -> list[LLMContext]:
        batch = []
        with contextlib.suppress(asyncio.TimeoutError):
            # Our initial timeout is infinite (None),
            # until we receive the first message.
            async with async_timeout.timeout(None) as cm:
                while len(batch) < self._batch_size:
                    enqueued_time, ctx = await self._queue.get()
                    batch.append(ctx)

                    # After we receive the first message
                    # we have to set a deadline
                    if cm.deadline is None:
                        time_passed = time.monotonic() - enqueued_time
                        time_left = self._window_size - time_passed

                        if time_left > 0.0:
                            cm.update(asyncio.get_running_loop().time() + time_left)
                        else:
                            # When head of queue has already expired
                            # the best strategy is:
                            #   * fill batch as full as possible
                            #   * exit immediately
                            elements_to_fill = min(
                                self._queue.qsize(), self._batch_size - 1
                            )
                            for _ in range(elements_to_fill):
                                _, ctx = await self._queue.get()
                                batch.append(ctx)

                            return batch
        return batch

    async def run(self):
        try:
            self._is_running = True
            while True:
                batch = await self._fill_batch()
                infer.enqueue(batch)
        finally:
            self._is_running = False

    def close(self):
        if not self._is_running:
            return
        self._background_task.cancel()

    def is_running(self) -> bool:
        return self._is_running

    def add_context_to_batch(self, context: LLMContext):
        if not self._is_running:
            raise RuntimeError("Trying to batch context with stopped %r", self)

        logger.info("Adding context %r to batch", context)
        self._queue.put_nowait((time.monotonic(), context))

    async def __aenter__(self) -> "ContextBatcher":
        if self._is_running:
            raise RuntimeError("Trying to launch running ContextBatcher")

        self._background_task = spawn(self.run())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.close()
        with contextlib.suppress(asyncio.CancelledError):
            await self._background_task
