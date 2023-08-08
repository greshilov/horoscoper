from pathlib import Path

from pydantic_settings import BaseSettings

ROOT = Path(__file__).parents[1]


class Settings(BaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    horoscope_csv_file: Path = ROOT / "etc" / "horoscopes.csv"


settings = Settings()
