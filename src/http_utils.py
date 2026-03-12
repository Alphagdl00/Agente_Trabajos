# src/http_utils.py

from __future__ import annotations

import logging
import random
import time
from typing import Any

import requests

from config.settings import settings


logger = logging.getLogger(__name__)


def create_session(api_mode: bool = False) -> requests.Session:
    """Crea una sesión HTTP con headers razonables."""
    session = requests.Session()

    headers = {
        "User-Agent": random.choice(settings.USER_AGENTS),
        "Accept-Language": settings.HTTP_ACCEPT_LANGUAGE,
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    }

    if api_mode:
        headers["Accept"] = "application/json, text/plain, */*"
    else:
        headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
        headers["Upgrade-Insecure-Requests"] = "1"

    session.headers.update(headers)
    return session


def respectful_delay(api_mode: bool = False) -> None:
    """Pausa aleatoria. Más suave para APIs, normal para HTML genérico."""
    if api_mode:
        delay = random.uniform(settings.API_DELAY_MIN, settings.API_DELAY_MAX)
    else:
        delay = random.uniform(settings.REQUEST_DELAY_MIN, settings.REQUEST_DELAY_MAX)

    if delay > 0:
        time.sleep(delay)


def safe_request(
    session: requests.Session,
    method: str,
    url: str,
    *,
    api_mode: bool = False,
    apply_delay: bool = True,
    **kwargs: Any,
) -> requests.Response | None:
    """
    Wrapper seguro para requests.
    Devuelve Response o None si falla.
    """
    kwargs.setdefault("timeout", settings.REQUEST_TIMEOUT)

    try:
        if apply_delay:
            respectful_delay(api_mode=api_mode)

        response = session.request(method=method.upper(), url=url, **kwargs)
        response.raise_for_status()
        return response
    except Exception as exc:
        logger.warning("HTTP %s failed for %s: %s", method.upper(), url, exc)
        return None