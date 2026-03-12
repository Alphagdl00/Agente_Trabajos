# config/settings.py

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


class Settings:
    """Configuración centralizada del proyecto."""

    BASE_DIR: Path = BASE_DIR
    OUTPUT_DIR: Path = BASE_DIR / "output"
    HISTORY_DIR: Path = BASE_DIR / "history"
    CACHE_DIR: Path = BASE_DIR / "cache"
    CONFIG_DIR: Path = BASE_DIR / "config"

    # Delay para scraping HTML genérico
    REQUEST_DELAY_MIN: float = float(os.getenv("REQUEST_DELAY_MIN", "1.0"))
    REQUEST_DELAY_MAX: float = float(os.getenv("REQUEST_DELAY_MAX", "2.5"))

    # Delay para APIs estructuradas (Workday / Greenhouse / Lever)
    API_DELAY_MIN: float = float(os.getenv("API_DELAY_MIN", "0.0"))
    API_DELAY_MAX: float = float(os.getenv("API_DELAY_MAX", "0.15"))

    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "20"))

    # Límite opcional de páginas Workday por empresa
    # 0 = sin límite
    WORKDAY_MAX_PAGES: int = int(os.getenv("WORKDAY_MAX_PAGES", "25"))

    HTTP_ACCEPT_LANGUAGE: str = os.getenv(
        "HTTP_ACCEPT_LANGUAGE",
        "en-US,en;q=0.9,es;q=0.8",
    )

    USER_PROFILE: str = os.getenv("USER_PROFILE", "").strip()

    USER_AGENTS: list[str] = [
        (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/605.1.15 (KHTML, like Gecko) "
            "Version/17.4 Safari/605.1.15"
        ),
        (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
    ]

    @classmethod
    def ensure_dirs(cls) -> None:
        cls.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        cls.HISTORY_DIR.mkdir(parents=True, exist_ok=True)
        cls.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cls.CONFIG_DIR.mkdir(parents=True, exist_ok=True)

    @classmethod
    def validate(cls) -> None:
        if cls.REQUEST_DELAY_MIN < 0:
            cls.REQUEST_DELAY_MIN = 0.0

        if cls.REQUEST_DELAY_MAX < cls.REQUEST_DELAY_MIN:
            cls.REQUEST_DELAY_MAX = cls.REQUEST_DELAY_MIN

        if cls.API_DELAY_MIN < 0:
            cls.API_DELAY_MIN = 0.0

        if cls.API_DELAY_MAX < cls.API_DELAY_MIN:
            cls.API_DELAY_MAX = cls.API_DELAY_MIN

        if cls.REQUEST_TIMEOUT <= 0:
            cls.REQUEST_TIMEOUT = 20

        if cls.WORKDAY_MAX_PAGES < 0:
            cls.WORKDAY_MAX_PAGES = 0


settings = Settings()
settings.validate()