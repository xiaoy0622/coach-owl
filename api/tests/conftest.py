"""Pytest fixtures: an isolated ``coachowl_test`` database + ASGI client."""
from __future__ import annotations

import os
from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from starlette.testclient import TestClient

from app.core.db import Base, get_db
from app.main import app

ADMIN_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/postgres",
)
TEST_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5434/coachowl_test",
)


@pytest.fixture(scope="session", autouse=True)
def _create_test_database() -> Iterator[None]:
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text("DROP DATABASE IF EXISTS coachowl_test WITH (FORCE)")
        )
        conn.execute(text("CREATE DATABASE coachowl_test"))
    admin.dispose()
    yield
    admin = create_engine(ADMIN_URL, isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        conn.execute(
            text("DROP DATABASE IF EXISTS coachowl_test WITH (FORCE)")
        )
    admin.dispose()


@pytest.fixture(scope="session")
def engine(_create_test_database):
    eng = create_engine(TEST_URL, future=True)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def session_factory(engine):
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


@pytest.fixture(autouse=True)
def _clean_tables(engine) -> Iterator[None]:
    yield
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db(session_factory) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(session_factory) -> Iterator[TestClient]:
    def _override_get_db() -> Iterator[Session]:
        session = session_factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
