"""Reuses the isolated Postgres test database set up in tests/api/conftest.py - reports
tests need a real DB session (aggregator queries feedback/analysis/theme/context tables)
but not a FastAPI TestClient."""

import pytest

import app.models  # noqa: F401 - populates Base.metadata
from tests.api.conftest import Base, TestingSessionLocal, engine


@pytest.fixture(scope="session", autouse=True)
def _ensure_tables():
    Base.metadata.create_all(bind=engine)  # no-op if tests/api's conftest already ran drop_all/create_all
    yield


@pytest.fixture()
def db_session():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
    with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            conn.execute(table.delete())
