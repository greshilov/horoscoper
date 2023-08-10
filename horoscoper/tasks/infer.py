import logging
from enum import Enum
from typing import Optional

from pydantic import BaseModel
from redis import Redis
from redis.utils import pipeline
from rq import Queue

from horoscoper.horoscope import LLMContext, get_model
from horoscoper.settings import settings

logger = logging.getLogger(__name__)
queue = Queue(connection=Redis())


class InferMessageStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class InferMessage(BaseModel):
    parts: list[str]
    error: Optional[str] = None
    status: InferMessageStatus


def enqueue(contexts: list[LLMContext]):
    logger.info("Enqueue %r contexts: %r", len(contexts), contexts)
    return queue.enqueue(process, contexts)


def process(contexts: list[LLMContext]):
    logger.info("Starting to process batch of contexts (%r)", contexts)

    horoscope_model = get_model()
    redis_client = Redis.from_url(settings.redis_url)

    for batch in horoscope_model.infer_batch(contexts=contexts):
        with pipeline(redis_client) as pipe:
            for context, infer_result in batch:
                status = (
                    InferMessageStatus.IN_PROGRESS
                    if not infer_result.is_last_chunk
                    else InferMessageStatus.FINISHED
                )

                pipe.publish(
                    channel=context.redis_key,
                    message=InferMessage(
                        parts=[infer_result.text], status=status
                    ).model_dump_json(),
                )

    logger.info("Finished processing batch of contexts (%r)", contexts)
