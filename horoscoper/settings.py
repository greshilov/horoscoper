from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).parents[1]
LOGGER = ROOT.name
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(levelprefix)s %(name)s %(message)s",
            "use_colors": None,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
    },
    "loggers": {
        LOGGER: {"handlers": ["default"], "level": "ERROR", "propagate": False},
    },
}


def setup_logging():
    import logging
    import logging.config

    logging.config.dictConfig(LOGGING_CONFIG)
    logging.getLogger(LOGGER).setLevel(logging.getLevelName(settings.log_level))


class Settings(BaseSettings):
    batcher_batch_size: int = 4
    batcher_window_ms: int = 250
    horoscope_csv_file: Path = ROOT / "etc" / "horoscopes.csv"
    redis_url: str = "redis://localhost:6379/0"
    log_level: str = "INFO"


settings = Settings()
