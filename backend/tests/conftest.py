from __future__ import annotations

import os
from collections.abc import Iterator
from urllib.parse import urlsplit

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from backend.app.models.base import Base
from backend.app.models.document_chunk import DocumentChunk
from backend.app.models.knowledge_document import KnowledgeDocument


def _test_database_url() -> str:
    url = os.getenv("TEST_DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL is not configured.")

    parsed = urlsplit(url)
    hostname = (parsed.hostname or "").lower()
    application_url = os.getenv("DATABASE_URL")
    if (
        "supabase" in hostname
        or hostname.endswith(".supabase.co")
        or url == application_url
    ):
        pytest.fail(
            "TEST_DATABASE_URL must not point to Supabase or match DATABASE_URL.",
            pytrace=False,
        )
    return url


@pytest.fixture
def database_engine() -> Iterator[Engine]:
    engine = create_engine(_test_database_url())
    Base.metadata.create_all(
        engine,
        tables=[KnowledgeDocument.__table__, DocumentChunk.__table__],
    )
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            connection.execute(text("DROP INDEX uq_knowledge_documents_active_key"))
            connection.execute(
                text(
                    "CREATE UNIQUE INDEX uq_knowledge_documents_active_key "
                    "ON knowledge_documents (document_key) WHERE is_active = 1"
                )
            )
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def database_session(database_engine: Engine) -> Iterator[Session]:
    with Session(database_engine) as session:
        transaction = session.begin()
        try:
            yield session
        finally:
            transaction.rollback()
