from __future__ import annotations

from contextlib import contextmanager
from urllib.parse import urlsplit, urlunsplit

from config.settings import settings

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency during local setup
    psycopg = None


def is_database_enabled() -> bool:
    return bool(settings.DATABASE_URL and psycopg is not None)


def to_psycopg_conninfo(database_url: str) -> str:
    normalized = (database_url or "").strip()
    if not normalized:
        return normalized

    # SQLAlchemy URLs may include an explicit driver like postgresql+psycopg://
    # but psycopg.connect() expects a plain PostgreSQL URL / conninfo string.
    if normalized.startswith("postgresql+psycopg://"):
        normalized = normalized.replace("postgresql+psycopg://", "postgresql://", 1)
    elif normalized.startswith("postgresql+psycopg2://"):
        normalized = normalized.replace("postgresql+psycopg2://", "postgresql://", 1)

    parts = urlsplit(normalized)
    return urlunsplit(parts)


@contextmanager
def get_connection():
    if not is_database_enabled():
        yield None
        return

    conn = psycopg.connect(to_psycopg_conninfo(settings.DATABASE_URL))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
