import logging
import time
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from prometheus_client import Counter, Histogram
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from horoscoper.llm import LLMContext
from horoscoper.settings import settings
from horoscoper.tasks.infer import InferMessage, InferMessageStatus

from .state import State

API_DIR = Path(__file__).parent

infer_first_response = Histogram(
    "api_infer_first_response", "Infer API first response latency"
)
infer_messages_count = Counter(
    "api_infer_messages_count", "InferMessage counter in API", ["status"]
)

logger = logging.getLogger(__name__)
router = APIRouter()
templates = Jinja2Templates(directory=API_DIR / "templates")


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
async def index(request: Request):
    return templates.TemplateResponse("index.html", context={"request": request})


@router.get("/healthcheck", include_in_schema=False)
async def healthcheck(state: State):
    if not state.batcher.is_running():
        raise HTTPException(status_code=500, detail="API unhealthy")


class APIInferRequest(BaseModel):
    prefix: str = Field(max_length=1024)


@router.post("/api/v1/infer")
async def infer(request: Request, state: State, infer_request: APIInferRequest):
    context = LLMContext(prefix=infer_request.prefix)
    await state.batcher.add_context_to_batch(context)

    start_infer = time.monotonic()

    async def iter_infer_response():
        first_message = True

        async with state.redis.pubsub() as pubsub:
            await pubsub.subscribe(context.redis_key)

            while True:
                # In case client drops the connection
                if await request.is_disconnected():
                    return

                raw_message = await pubsub.get_message(timeout=settings.infer_job_ttl)
                if raw_message is None:
                    logger.info("Timeout inference for %r", context)
                    error_msg = InferMessage(
                        status=InferMessageStatus.ERROR,
                        text="",
                        error="Timeout inference",
                    )
                    yield ServerSentEvent(data=error_msg.model_dump_json())
                    infer_messages_count.labels(
                        status=str(InferMessageStatus.ERROR)
                    ).inc()
                    return

                if raw_message["type"] == "subscribe":
                    continue

                json_data = raw_message["data"]
                infer_message = InferMessage.model_validate_json(json_data)
                infer_messages_count.labels(status=str(infer_message.status)).inc()

                if first_message:
                    infer_first_response.observe(time.monotonic() - start_infer)
                    first_message = False

                yield ServerSentEvent(data=json_data.decode())
                if infer_message.status in (
                    InferMessageStatus.ERROR,
                    InferMessageStatus.FINISHED,
                ):
                    return

    return EventSourceResponse(iter_infer_response())
