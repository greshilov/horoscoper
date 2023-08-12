from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Request
from redis.asyncio import Redis

from .batcher import ContextBatcher


@dataclass
class AppState:
    """
    FastAPI has built-in `DependencyInjection` framework, where
    dependencies are usually classes/functions defined on the module level.

    It works great with simple objects, but becomes pain in the neck for
    any asynchronously initialized objects. They are tightly coupled with
    `EventLoop` which is simply doesn't exist during the import time.

    This class is approach to solve this issue by creating dependency that is
    stored in `Application` object itself and initialized during `lifespan` call.
    """

    batcher: ContextBatcher
    redis: Redis


def get_app_state(request: Request) -> AppState:
    return request.app.state.app_state


State = Annotated[AppState, Depends(get_app_state)]
