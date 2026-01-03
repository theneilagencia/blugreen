from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.database import get_session
from app.main import app

# Import all models to ensure they are registered with SQLModel.metadata
from app.models import Agent, Project, Task, Workflow  # noqa: F401


@pytest.fixture(name="session")
def session_fixture():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override

    # Patch background task functions to prevent them from running during tests.
    # These tasks use get_session_context() which creates a new session from the
    # app's global engine, bypassing the test's dependency override.
    # Since these tests only verify the API contract (immediate response),
    # we don't need the background tasks to actually execute.
    async def noop_coroutine(*args, **kwargs):
        pass

    with (
        patch("app.api.product._run_product_creation", noop_coroutine),
        patch("app.api.assumption._run_assumption_task", noop_coroutine),
        patch("app.api.assumption._run_diagnostics_task", noop_coroutine),
        patch("app.api.assumption._run_evolution_task", noop_coroutine),
    ):
        client = TestClient(app)
        yield client

    app.dependency_overrides.clear()
