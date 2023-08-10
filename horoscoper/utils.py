import asyncio
import logging
import random
import time
import traceback
from contextlib import contextmanager
from typing import Coroutine

logger = logging.getLogger(__name__)


def produce_n_delays(overall_time: int, n: int) -> list[float]:
    delays = [random.random() for _ in range(n)]
    coeff = overall_time / sum(delays)
    return [delay * coeff for delay in delays]


def log_async_error(task: asyncio.Task):
    exc = task.exception()
    if exc:
        traceback.print_exception(exc)


def spawn(coro: Coroutine) -> asyncio.Task:
    """
    Safe background spawn, that logs exception to stderr.
    """
    task = asyncio.create_task(coro)
    task.add_done_callback(log_async_error)
    return task


@contextmanager
def timit(name: str):
    start = time.monotonic()
    try:
        yield
    finally:
        logger.info("%r took %r seconds", name, time.monotonic() - start)
