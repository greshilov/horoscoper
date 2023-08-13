# flake8: noqa

import random
import tempfile

import pytest

from horoscoper.horoscope import HoroscopeIndex, HoroscopeLLM, Sign
from horoscoper.llm import LLMContext, LLMInferResult


@pytest.fixture(scope="session")
def horoscope_file():
    test_csv = """source;ts;sign;text;type
mailru;2019-11-10 00:00:00;ARIES;"Вы многое принимаете близко к сердцу";DEFAULT
mailru;2019-11-11 00:00:00;LIBRA;"День обещает приятные встречи, интересные разговсотрудничества, финансов";DEFAULT
rambler;2019-11-14 00:00:00;ARIES;Овнов сегодня ждет ряд волнующих романтичных моментов в любви;DEFAULT"""

    with tempfile.NamedTemporaryFile() as fp:
        fp.write(test_csv.encode())
        fp.flush()
        yield fp.name


@pytest.mark.parametrize(
    "sign,expected",
    [
        [Sign.ARIES, "Вы многое принимаете близко к сердцу"],
        [Sign.CANCER, ""],
    ],
)
def test_horoscope_index(monkeypatch, horoscope_file, sign, expected):
    monkeypatch.setattr(random, "choice", lambda l: l[0])
    horoscope_index = HoroscopeIndex.load_from_csv(horoscope_file)
    assert horoscope_index.predict(sign) == expected


def test_horoscope_llm(monkeypatch, horoscope_file):
    monkeypatch.setattr(random, "choice", lambda l: l[0])
    llm = HoroscopeLLM(horoscope_file)
    llm.MIN_RESPONSE_TIME_MS = 0
    llm.MAX_RESPONSE_TIME_MS = 10

    prediction = list(llm.infer(LLMContext()))
    assert prediction == [
        LLMInferResult(text="Вы"),
        LLMInferResult(text="многое"),
        LLMInferResult(text="принимаете"),
        LLMInferResult(text="близко"),
        LLMInferResult(text="к"),
        LLMInferResult(text="сердцу", is_last_chunk=True),
    ]
