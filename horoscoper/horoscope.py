import csv
import random
import time
from enum import Enum
from functools import cache
from itertools import zip_longest
from pathlib import Path
from typing import Iterable

from horoscoper.llm import LLM, LLMContext
from horoscoper.settings import settings


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

    def predict(self, sign: Sign) -> str:
        if predictions := self._horoscopes[sign]:
            return random.choice(predictions)
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
    This class represents dummy LLM, that generates horoscope based on supplied context(s).
    Generation process is artifically slowed down to mimic real LLM behaviour.
    Overall spent time for will be be in [MIN_RESPONSE_TIME_MS, MAX_RESPONSE_TIME_MS] interval.
    """

    MIN_RESPONSE_TIME_MS = 500
    MAX_RESPONSE_TIME_MS = 2500

    def __init__(self, horoscope_csv_file: Path):
        self.horoscope_index = HoroscopeIndex.load_from_csv(horoscope_csv_file)

    def _infer(self, context: LLMContext) -> list[str]:
        prediction = self.horoscope_index.predict(random.choice(list(Sign)))
        words = prediction.split(" ")
        return words

    def infer(self, context: LLMContext) -> Iterable[str]:
        """Produce a horoscope based on the supplied context"""
        words = self._infer(context)

        overall_time = random.randint(
            self.MIN_RESPONSE_TIME_MS, self.MAX_RESPONSE_TIME_MS
        )
        delays = [random.random() for _ in range(len(words))]
        coeff = overall_time / sum(delays)
        delays = [delay * coeff for delay in delays]

        for word, delay in zip(words, delays):
            time.sleep(delay / 1000)
            yield word

    def infer_batch(
        self, contexts: list[LLMContext]
    ) -> Iterable[list[tuple[LLMContext, str]]]:
        """Produce a horoscope for multiple contexts"""

        words_batch = [(context, self._infer(context)) for context in contexts]

        max_words = max(len(words) for _, words in words_batch)

        overall_time = random.randint(
            self.MIN_RESPONSE_TIME_MS, self.MAX_RESPONSE_TIME_MS
        )
        delays = [random.random() for _ in range(max_words)]
        coeff = overall_time / sum(delays)
        delays = [delay * coeff for delay in delays]

        for i in range(max_words):
            time.sleep(delays[i] / 1000)

            batch = []
            for context, words in words_batch:
                if i < len(words):
                    batch.append((context, words[i]))
            yield batch


@cache
def get_model() -> HoroscopeLLM:
    return HoroscopeLLM(horoscope_csv_file=settings.horoscope_csv_file)
