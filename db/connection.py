from __future__ import annotations

from contextlib import contextmanager

from config.settings import settings

try:
    import psycopg
except Exception:  # pragma: no cover - optional dependency during local setup
    psycopg = None


def is_database_enabled() -> bool:
    return bool(settings.DATABASE_URL and psycopg is not None)


@contextmanager
def get_connection():
    if not is_database_enabled():
        yield None
        return

    conn = psycopg.connect(settings.DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
