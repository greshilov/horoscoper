from contextlib import AsyncExitStack, asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI

from horoscoper.settings import settings

from .batcher import ContextBatcher
from .state import AppState
from .views import router


@asynccontextmanager
async def lifespan(app_: FastAPI):
    async with AsyncExitStack() as stack:
        batcher = await stack.enter_async_context(ContextBatcher())
        redis_client = await stack.enter_async_context(
            redis.from_url(settings.redis_url)
        )
        app_.state.app_state = AppState(batcher=batcher, redis=redis_client)
        yield


app = FastAPI(
    title="Horoscoper API",
    description="Convenient API that provide you with horoscopes"
    "pretending they generated using LLM.",
    lifespan=lifespan,
)

app.include_router(router)