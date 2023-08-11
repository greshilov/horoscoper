import asyncio
import functools
import logging
import random
import sys
import traceback
from typing import Coroutine

logger = logging.getLogger(__name__)


def sync_to_async(func):
    @functools.wraps(func)
    async def wraps(*args, **kwargs):
        loop = asyncio.get_running_loop()
        argless_func = functools.partial(func, *args, **kwargs)
        return await loop.run_in_executor(None, argless_func)

    return wraps


def produce_n_delays(overall_time: int, n: int) -> list[float]:
    delays = [random.random() for _ in range(n)]
    coeff = overall_time / sum(delays)
    return [delay * coeff for delay in delays]


def log_async_error(task: asyncio.Task):
    try:
        exc = task.exception()
    except asyncio.CancelledError:
        pass
    else:
        if exc:
            traceback.print_exception(exc, file=sys.stderr)


def spawn(coro: Coroutine) -> asyncio.Task:
    """
    Safe background spawn, that logs exception to stderr.
    """
    task = asyncio.create_task(coro)
    task.add_done_callback(log_async_error)
    return task
