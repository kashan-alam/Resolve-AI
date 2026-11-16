from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import settings


def create_database_engine():
    if not settings.database_url:
        raise RuntimeError(
            "DATABASE_URL is required for database operations. "
            "Set it in backend/.env."
        )

    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
    )


engine = create_database_engine() if settings.database_url else None
SessionLocal = (
    sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    if engine
    else None
)


def get_db() -> Generator[Session, None, None]:
    if SessionLocal is None:
        raise RuntimeError(
            "Database session requested before DATABASE_URL was configured."
        )

    with SessionLocal() as session:
        yield session
