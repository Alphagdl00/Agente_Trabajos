# src/http_utils.py

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

from config.settings import settings


logger = logging.getLogger(__name__)


def create_session() -> requests.Session:
    """Crea una sesión HTTP con headers razonables."""
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": random.choice(settings.USER_AGENTS),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": settings.HTTP_ACCEPT_LANGUAGE,
            "Accept-Encoding": "gzip, deflate",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    )
    return session


def respectful_delay() -> None:
    """Pausa aleatoria entre requests para no disparar scraping agresivo."""
    delay = random.uniform(settings.REQUEST_DELAY_MIN, settings.REQUEST_DELAY_MAX)
    time.sleep(delay)


def safe_request(
    session: requests.Session,
    method: str,
    url: str,
    **kwargs: Any,
) -> requests.Response | None:
    """
    Wrapper seguro para requests.
    Devuelve Response o None si falla.
    """
    kwargs.setdefault("timeout", settings.REQUEST_TIMEOUT)

    try:
        respectful_delay()
        response = session.request(method=method.upper(), url=url, **kwargs)
        response.raise_for_status()
        return response
    except Exception as exc:
        logger.warning("HTTP %s failed for %s: %s", method.upper(), url, exc)
        return None