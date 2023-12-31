import csv
import hashlib
import random
import time
from enum import Enum
from functools import cache
from pathlib import Path
from typing import Iterable

from horoscoper.llm import LLM, LLMContext, LLMInferBatchResult, LLMInferResult
from horoscoper.settings import settings
from horoscoper.utils import produce_n_delays


class Sign(str, Enum):
    ARIES = "ARIES"
    TAURUS = "TAURUS"
    GEMINI = "GEMINI"
    CANCER = "CANCER"
    LEO = "LEO"
    VIRGO = "VIRGO"
    LIBRA = "LIBRA"
    SCORPIO = "SCORPIO"
    SAGITTARIUS = "SAGITTARIUS"
    CAPRICORN = "CAPRICORN"
    AQUARIUS = "AQUARIUS"
    PISCES = "PISCES"


class HoroscopeIndex:
    def __init__(self, horoscopes: dict[Sign, list[str]]):
        self._horoscopes = horoscopes

    def predict_by_prefix(self, prefix: str) -> str:
        prefix_hash = int(hashlib.sha256(prefix.encode()).hexdigest(), 16)
        signs = list(Sign)

        chosen_sign = signs[prefix_hash % len(signs)]
        predictions = self._horoscopes[chosen_sign]

        if len(predictions) > 0:
            return predictions[prefix_hash % len(predictions)]
        else:
            return ""

    @staticmethod
    def load_from_csv(csv_path: Path) -> "HoroscopeIndex":
        horoscopes = {sign: [] for sign in Sign}

        with open(csv_path) as csvfile:
            reader = csv.DictReader(csvfile, delimiter=";")

            for row in reader:
                horoscopes[Sign(row["sign"])].append(row["text"])

        return HoroscopeIndex(horoscopes=horoscopes)


class HoroscopeLLM(LLM):
    """
    Represents dummy LLM, that generates horoscope based on supplied context(s).
    Generation process is artificially slowed down to mimic real LLM behaviour.
    Overall spent time for inference will be in:
        [MIN_RESPONSE_TIME_MS, MAX_RESPONSE_TIME_MS] interval.
    """

    MIN_RESPONSE_TIME_MS = 500
    MAX_RESPONSE_TIME_MS = 3000

    def __init__(self, horoscope_csv_file: Path):
        self._horoscope_index = HoroscopeIndex.load_from_csv(horoscope_csv_file)

    def _infer(self, context: LLMContext) -> list[str]:
        prediction = self._horoscope_index.predict_by_prefix(context.prefix)
        words = prediction.split(" ")
        return words

    def infer(self, context: LLMContext) -> Iterable[LLMInferResult]:
        """Generate horoscope based on the supplied context"""
        words = self._infer(context)

        overall_time = random.randint(
            self.MIN_RESPONSE_TIME_MS, self.MAX_RESPONSE_TIME_MS
        )
        delays = produce_n_delays(overall_time=overall_time, n=len(words))

        for i, (word, delay) in enumerate(zip(words, delays)):
            time.sleep(delay / 1000)

            is_last_chunk = i == len(words) - 1
            text = f"{word} " if not is_last_chunk else word
            yield LLMInferResult(
                text=text,
                is_last_chunk=is_last_chunk,
            )

    def infer_batch(self, contexts: list[LLMContext]) -> Iterable[LLMInferBatchResult]:
        """Generate horoscope for multiple contexts"""

        words_batch = [(context, self._infer(context)) for context in contexts]

        max_words = max(len(words) for _, words in words_batch)
        overall_time = random.randint(
            self.MIN_RESPONSE_TIME_MS, self.MAX_RESPONSE_TIME_MS
        )
        delays = produce_n_delays(overall_time=overall_time, n=max_words)

        for i in range(max_words):
            time.sleep(delays[i] / 1000)

            batch = []
            for context, words in words_batch:
                if i < len(words):
                    is_last_chunk = i == len(words) - 1
                    text = f"{words[i]} " if not is_last_chunk else words[i]

                    result = LLMInferResult(
                        is_last_chunk=is_last_chunk,
                        text=text,
                    )
                    batch.append((context, result))

            yield batch


@cache
def get_model() -> HoroscopeLLM:
    return HoroscopeLLM(horoscope_csv_file=settings.horoscope_csv_file)
