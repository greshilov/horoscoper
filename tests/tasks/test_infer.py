import fakeredis
import pytest

import horoscoper.tasks.infer
from horoscoper.horoscope import HoroscopeLLM
from horoscoper.llm import LLMContext
from horoscoper.tasks.infer import InferMessage, InferMessageStatus, process


@pytest.fixture
def patch_redis(monkeypatch):
    fake_redis = fakeredis.FakeRedis()
    monkeypatch.setattr(horoscoper.tasks.infer, "get_redis", lambda: fake_redis)
    yield fake_redis


@pytest.fixture
def patch_get_model(monkeypatch):
    class FakeHoroscopeLLM(HoroscopeLLM):
        MIN_RESPONSE_TIME_MS = 0
        MAX_RESPONSE_TIME_MS = 10

        def __init__(self, *args, **kwargs):
            pass

        def _infer(self, context: LLMContext):
            return ["Hello", "world", "!"]

    fake_horoscope_llm = FakeHoroscopeLLM()
    monkeypatch.setattr(horoscoper.tasks.infer, "get_model", lambda: fake_horoscope_llm)
    yield fake_horoscope_llm


def test_infer_process(patch_get_model, patch_redis):
    contexts = [LLMContext(prefix="random"), LLMContext(prefix="cat")]

    context_key_1 = contexts[0].redis_key
    context_key_2 = contexts[1].redis_key

    pubsub_1 = patch_redis.pubsub()
    pubsub_2 = patch_redis.pubsub()

    pubsub_1.subscribe(context_key_1)
    pubsub_2.subscribe(context_key_2)

    def read_from_pubsub(pubsub):
        received_messages = []
        while True:
            raw_message = pubsub.get_message()
            if raw_message["type"] == "subscribe":
                continue

            json_data = raw_message["data"]
            infer_message = InferMessage.model_validate_json(json_data)

            received_messages.append(infer_message)

            if infer_message.status in (
                InferMessageStatus.ERROR,
                InferMessageStatus.FINISHED,
            ):
                break
        return received_messages

    process(contexts=contexts)

    received_messages_1 = read_from_pubsub(pubsub_1)
    received_messages_2 = read_from_pubsub(pubsub_2)

    expected = [
        InferMessage(text="Hello ", status=InferMessageStatus.IN_PROGRESS),
        InferMessage(text="world ", status=InferMessageStatus.IN_PROGRESS),
        InferMessage(text="!", status=InferMessageStatus.FINISHED),
    ]

    assert received_messages_1 == expected, "First subscriber received all messages"
    assert received_messages_2 == expected, "Second subscriber received all messages"
