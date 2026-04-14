from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _create_engine():
    settings = get_settings()
    url = settings.resolved_database_url()
    connect_args = {}
    if url.startswith("sqlite"):
        connect_args["check_same_thread"] = False
    return create_engine(url, connect_args=connect_args)


engine = _create_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    from app.models import garment  # noqa: F401 — register models

    settings = get_settings()
    db_path = settings.resolved_database_url()
    if db_path.startswith("sqlite:///"):
        path_part = db_path.removeprefix("sqlite:///")
        Path(path_part).parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
