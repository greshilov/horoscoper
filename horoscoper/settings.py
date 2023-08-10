from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).parents[1]


class Settings(BaseSettings):
    batcher_batch_size: int = 4
    batcher_window_ms: int = 250
    horoscope_csv_file: Path = ROOT / "etc" / "horoscopes.csv"
    redis_url: str = "redis://localhost:6379/0"


settings = Settings()
