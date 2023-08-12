import asyncio
import contextlib
import logging
import time

import async_timeout
from prometheus_client import Gauge

from horoscoper.llm import LLMContext
from horoscoper.tasks import infer
from horoscoper.utils import spawn

logger = logging.getLogger(__name__)
QueueObject = tuple[float, LLMContext]

queue_size_gauge = Gauge("context_batcher_queue_size", "Queue size for context batcher")
batch_size = Gauge("context_batcher_batch_size", "Size of the scheduled batch")


class ContextBatcher:
    def __init__(self, batch_size: int, window_size_ms: int):
        self._queue: asyncio.Queue[QueueObject] = asyncio.Queue()
        self._is_running = False
        self._background_task = None
        self._batch_size = batch_size
        self._window_size = window_size_ms / 1000

    async def run(self):
        try:
            while True:
                batch = await self._fill_batch()
                await infer.enqueue_async(batch)

                queue_size_gauge.set(self._queue.qsize())
                batch_size.set(len(batch))
        finally:
            self._is_running = False

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
                        time_passed = max(time.monotonic() - enqueued_time, 0)
                        time_left = self._window_size - time_passed

                        if time_left > 0.0:
                            cm.update(asyncio.get_running_loop().time() + time_left)
                        else:
                            # When the head of the queue has already expired
                            # the best strategy would be:
                            #   * fill batch as full as possible
                            #   * exit immediately
                            available_contexts = min(
                                self._queue.qsize(), self._batch_size - 1
                            )
                            for _ in range(available_contexts):
                                _, ctx = self._queue.get_nowait()
                                batch.append(ctx)

                            return batch
        return batch

    async def start(self):
        if self._is_running:
            return

        self._is_running = True
        self._background_task = spawn(self.run())

    async def stop(self):
        if not self._is_running:
            return

        logger.info("Gracefully stopping ContextBatcher")
        self._background_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._background_task

    def is_running(self) -> bool:
        return self._is_running

    async def add_context_to_batch(self, context: LLMContext):
        """
        This method is made asynchronous in case we make underlying
        queue bounded (to mitigate backpressure for example).
        """
        if not self._is_running:
            raise RuntimeError("Trying to batch context with stopped ContextBatcher")

        logger.info("Adding context %r to batch", context)
        await self._queue.put((time.monotonic(), context))
        queue_size_gauge.inc()

    async def __aenter__(self) -> "ContextBatcher":
        if self._is_running:
            raise RuntimeError("Trying to launch running ContextBatcher")

        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()
