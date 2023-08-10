import asyncio
import logging
import time
from typing import Union

from horoscoper.llm import LLMContext
from horoscoper.settings import settings
from horoscoper.tasks import infer
from horoscoper.utils import spawn

logger = logging.getLogger(__name__)

QueueSignal = object
QueueObject = Union[QueueSignal, tuple[int, LLMContext]]


class ContextBatcher:
    EXIT = QueueSignal()

    def __init__(self):
        self._queue: asyncio.Queue[QueueObject] = asyncio.Queue()
        self._is_running = False
        self._background_task = None

    async def run(self):
        try:
            self._is_running = True
            while True:
                message = await self._queue.get()
                if message is self.EXIT:
                    logger.info("Gracefully stopping ContextBatcher")
                    return

                enqueued_time, ctx = message
                window_time_left = settings.batcher_window_ms / 1000 - (
                    time.monotonic() - enqueued_time
                )

                if window_time_left > 0:
                    await asyncio.sleep(window_time_left)

                batch = [ctx]
                logger.info("Queue size: %r", self._queue.qsize())

                elements_left = min(
                    self._queue.qsize(), settings.batcher_batch_size - 1
                )
                logger.info("Elements left: %r", elements_left)
                for _ in range(elements_left):
                    _, ctx = self._queue.get_nowait()
                    batch.append(ctx)

                infer.enqueue(batch)
        finally:
            self._is_running = False

    def close(self):
        if not self._is_running:
            return
        self._queue.put_nowait(self.EXIT)

    def is_running(self):
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
        await self._background_task
