import logging
import os
from enum import Enum
from functools import cache
from typing import Optional

import rq
from pydantic import BaseModel
from redis import Redis
from redis.utils import pipeline

from horoscoper.horoscope import LLMContext, get_model
from horoscoper.settings import settings, setup_logging
from horoscoper.utils import sync_to_async

logger = logging.getLogger(__name__)


class InferMessageStatus(str, Enum):
    IN_PROGRESS = "IN_PROGRESS"
    FINISHED = "FINISHED"
    ERROR = "ERROR"


class InferMessage(BaseModel, extra="allow"):
    """
    Message used for communication between API and Workers.
    """

    text: str
    status: InferMessageStatus
    error: Optional[str] = None


@cache
def get_redis() -> Redis:
    """
    Redis is cached, to get advantage from
    the connection pool under the hood.
    """
    return Redis.from_url(settings.redis_url)


@cache
def get_queue() -> rq.Queue:
    """
    Queue is loaded lazily to avoid redis
    connection creation during the import.
    """
    return rq.Queue(name="infer", connection=get_redis())


def enqueue(contexts: list[LLMContext], **kwargs):
    logger.info("Enqueue contexts: %r", contexts)
    return get_queue().enqueue(process, contexts, **kwargs)


enqueue_async = sync_to_async(enqueue)


def process(contexts: list[LLMContext]):
    logger.info("Starting to process batch of contexts (%r)", contexts)

    horoscope_model = get_model()
    redis_client = get_redis()

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
                        text=infer_result.text, status=status
                    ).model_dump_json(),
                )

    logger.info("Finished processing batch of contexts (%r)", contexts)


if __name__ == "__main__":
    setup_logging()
    get_model()  # Cache model in memory
    queue = get_queue()
    redis = get_redis()
    worker_name = f"worker-{os.getenv('HOSTNAME', 'localhost')}"
    worker = rq.Worker([queue], name=worker_name, connection=redis)
    worker.work()
