import uuid
from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from sse_starlette.sse import EventSourceResponse, ServerSentEvent

from horoscoper.llm import LLMContext
from horoscoper.settings import settings
from horoscoper.worker import InferMessage, InferMessageStatus, enqueue_context_batch


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = await redis.from_url(settings.redis_url)
    yield
    await app.state.redis.close()


app = FastAPI(
    title="Horoscoper API",
    description="Convenient API that provide you with horoscopes"
    "pretending they generated using LLM.",
    lifespan=lifespan,
)


@app.get("/")
async def index():
    return HTMLResponse(
        """
<html>
<body>
    <script>
        var sse = new EventSource("/api/v1/infer");
        sse.onmessage = function(e) {

            data = JSON.parse(e.data)
            response = document.getElementById("response")
            response.textContent += data["parts"][0]

            if (data["status"] == "FINISHED") {
                sse.close()
            } else {
                response.textContent += " "
            }
        }
    </script>
    <h1>Response from server:</h1>
    <div id="response"></div>
</body>
</html>
    """
    )


@app.get("/api/v1/infer")
async def infer(request: Request):
    context = LLMContext(conversation_id=uuid.uuid4(), prefix=[])
    enqueue_context_batch([context])

    async def iter_infer_response():
        async with app.state.redis.pubsub() as pubsub:
            await pubsub.subscribe(context.redis_key)

            while True:
                if await request.is_disconnected():
                    return

                raw_message = await pubsub.get_message(timeout=10)

                if raw_message is None:
                    return

                if raw_message["type"] == "subscribe":
                    continue

                json_data = raw_message["data"]
                infer_message = InferMessage.model_validate_json(json_data)

                yield ServerSentEvent(data=json_data.decode())

                if infer_message.status is InferMessageStatus.FINISHED:
                    return

    return EventSourceResponse(iter_infer_response())
