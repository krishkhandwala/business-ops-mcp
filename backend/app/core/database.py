import logging
from typing import Generator
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

logger = logging.getLogger("nexus.database")

Base = declarative_base()


def _build_engine():
    db_url = settings.DATABASE_URL
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url, connect_args={"check_same_thread": False}, future=True
        )
    try:
        eng = create_engine(
            db_url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 2},
            future=True,
        )
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("Connected to primary PostgreSQL database.")
        return eng
    except Exception as exc:
        logger.warning(
            "Primary PostgreSQL database unreachable (%s). Falling back to local database (%s).",
            str(exc).splitlines()[0] if str(exc) else "connection error",
            settings.FALLBACK_SQLITE_URL,
        )
        return create_engine(
            settings.FALLBACK_SQLITE_URL,
            connect_args={"check_same_thread": False},
            future=True,
        )


engine = _build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

