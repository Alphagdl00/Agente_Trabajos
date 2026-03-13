from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from config.settings import settings


Base = declarative_base()


def is_sqlalchemy_enabled() -> bool:
    return bool(settings.DATABASE_URL)


def build_engine():
    if not is_sqlalchemy_enabled():
        return None
    return create_engine(settings.DATABASE_URL, future=True, pool_pre_ping=True)


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True) if engine else None


@contextmanager
def get_session() -> Iterator[Session | None]:
    if SessionLocal is None:
        yield None
        return

    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_all() -> bool:
    if engine is None:
        return False
    Base.metadata.create_all(bind=engine)
    return True
