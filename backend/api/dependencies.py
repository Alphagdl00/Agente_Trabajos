from __future__ import annotations

from backend.core.db import get_session


def db_session_dependency():
    with get_session() as session:
        yield session
