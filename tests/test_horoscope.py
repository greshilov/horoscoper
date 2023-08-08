import random
import tempfile

import pytest

from horoscoper.horoscope import HoroscopeIndex, Sign


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
def test_horoscope_index(horoscope_file, sign, expected):
    random.seed(42)
    horoscope_index = HoroscopeIndex.load_from_csv(horoscope_file)
    assert horoscope_index.predict(sign) == expected
