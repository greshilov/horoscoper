import logging

from pydantic import BaseModel
from redis import Redis
from rq import Queue

from horoscoper.horoscope import LLMContext, get_model
from horoscoper.settings import settings

logger = logging.getLogger(__name__)
queue = Queue(connection=Redis())


class InferMessage(BaseModel):
    parts: list[str]


def process_context_batch(contexts: list[LLMContext]):
    logger.info(
        "Starting to process batch of %r contexts (%r)", len(contexts), contexts
    )

    horoscope_model = get_model()
    redis_client = Redis.from_url(settings.redis_url)

    for batch in horoscope_model.infer_batch(contexts=contexts):
        pipe = redis_client.pipeline()
        for context, word in batch:
            pipe.publish(
                channel=context.redis_key, message=InferMessage(parts=[word]).json()
            )
        pipe.execute()

    logger.info(
        "Finished processing batch of %r contexts (%r)", len(contexts), contexts
    )
