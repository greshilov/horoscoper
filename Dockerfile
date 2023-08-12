
FROM python:3.11

MAINTAINER Slava Greshilov <s@greshilov.me>
ENV PIP_NO_CACHE_DIR=1

COPY poetry.lock pyproject.toml ./
RUN pip install poetry==1.5.1 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --without dev

COPY horoscoper horoscoper
COPY etc etc

CMD ["uvicorn", "horoscoper.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
