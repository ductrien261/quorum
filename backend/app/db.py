from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_SessionLocal: sessionmaker | None = None


def get_engine(url: str | None = None):
    global _engine, _SessionLocal
    if _engine is None or url is not None:
        url = url or get_settings().database_url
        kwargs = {}
        if url.startswith("sqlite"):
            path = url.replace("sqlite:///", "")
            if path and path != ":memory:":
                Path(path).parent.mkdir(parents=True, exist_ok=True)
            kwargs["connect_args"] = {"check_same_thread": False}
        _engine = create_engine(url, future=True, **kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(_engine, "connect")
            def _pragma(dbapi_conn, _):  # noqa: ANN001
                cur = dbapi_conn.cursor()
                cur.execute("PRAGMA journal_mode=WAL")
                cur.execute("PRAGMA foreign_keys=ON")
                cur.close()
        _SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False, future=True)
    return _engine


def init_db(url: str | None = None) -> None:
    from . import models  # noqa: F401  (register tables)

    Base.metadata.create_all(get_engine(url))


def SessionLocal() -> Session:
    get_engine()
    assert _SessionLocal is not None
    return _SessionLocal()


@contextmanager
def session_scope() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()


def get_db() -> Iterator[Session]:
    s = SessionLocal()
    try:
        yield s
    finally:
        s.close()
