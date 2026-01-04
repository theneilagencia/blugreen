"""
Tests for bulletproof DELETE endpoint.

REGRA ABSOLUTA:
- DELETE nunca retorna 500 por regra de negócio
- CORS sempre presente
- Mensagens estruturadas
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models.project import Project, ProjectStatus


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with database session."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def test_delete_terminated_project_success(client: TestClient, session: Session):
    """DELETE returns 200 for TERMINATED project."""
    # Create TERMINATED project
    project = Project(
        name="Test Project",
        description="Test",
        status=ProjectStatus.TERMINATED
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    
    # DELETE should succeed
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 200
    assert response.json() == {
        "status": "deleted",
        "project_id": project.id
    }
    
    # Verify CORS headers
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"


def test_delete_active_project_blocked(client: TestClient, session: Session):
    """DELETE returns 409 for ACTIVE project."""
    # Create ACTIVE project
    project = Project(
        name="Active Project",
        description="Test",
        status=ProjectStatus.ACTIVE
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    
    # DELETE should be blocked
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 409
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_TERMINATED"
    assert "encerrado" in data["message"].lower()
    
    # Verify CORS headers
    assert "access-control-allow-origin" in response.headers


def test_delete_draft_project_blocked(client: TestClient, session: Session):
    """DELETE returns 409 for DRAFT project."""
    # Create DRAFT project
    project = Project(
        name="Draft Project",
        description="Test",
        status=ProjectStatus.DRAFT
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    
    # DELETE should be blocked
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 409
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_TERMINATED"
    
    # Verify CORS headers
    assert "access-control-allow-origin" in response.headers


def test_delete_nonexistent_project(client: TestClient):
    """DELETE returns 404 for nonexistent project."""
    response = client.delete(
        "/projects/99999",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"
    
    # Verify CORS headers
    assert "access-control-allow-origin" in response.headers


def test_delete_idempotent(client: TestClient, session: Session):
    """DELETE is idempotent (second DELETE returns 404, not 500)."""
    # Create TERMINATED project
    project = Project(
        name="Test Project",
        description="Test",
        status=ProjectStatus.TERMINATED
    )
    session.add(project)
    session.commit()
    session.refresh(project)
    project_id = project.id
    
    # First DELETE succeeds
    response1 = client.delete(f"/projects/{project_id}")
    assert response1.status_code == 200
    
    # Second DELETE returns 404 (not 500)
    response2 = client.delete(f"/projects/{project_id}")
    assert response2.status_code == 404
    assert response2.json()["error_code"] == "PROJECT_NOT_FOUND"


def test_delete_cors_always_present(client: TestClient, session: Session):
    """CORS headers present in all responses (200, 404, 409)."""
    origin = "https://app.blugreen.com.br"
    
    # 404 scenario
    response_404 = client.delete("/projects/99999", headers={"Origin": origin})
    assert "access-control-allow-origin" in response_404.headers
    
    # 409 scenario (ACTIVE project)
    project_active = Project(name="Active", status=ProjectStatus.ACTIVE)
    session.add(project_active)
    session.commit()
    session.refresh(project_active)
    
    response_409 = client.delete(f"/projects/{project_active.id}", headers={"Origin": origin})
    assert "access-control-allow-origin" in response_409.headers
    
    # 200 scenario (TERMINATED project)
    project_terminated = Project(name="Terminated", status=ProjectStatus.TERMINATED)
    session.add(project_terminated)
    session.commit()
    session.refresh(project_terminated)
    
    response_200 = client.delete(f"/projects/{project_terminated.id}", headers={"Origin": origin})
    assert "access-control-allow-origin" in response_200.headers


def test_delete_returns_structured_json(client: TestClient, session: Session):
    """All DELETE responses return structured JSON."""
    # 404 response
    response_404 = client.delete("/projects/99999")
    assert response_404.headers["content-type"] == "application/json"
    data_404 = response_404.json()
    assert "error_code" in data_404
    assert "message" in data_404
    
    # 409 response
    project_active = Project(name="Active", status=ProjectStatus.ACTIVE)
    session.add(project_active)
    session.commit()
    session.refresh(project_active)
    
    response_409 = client.delete(f"/projects/{project_active.id}")
    assert response_409.headers["content-type"] == "application/json"
    data_409 = response_409.json()
    assert "error_code" in data_409
    assert "message" in data_409
    
    # 200 response
    project_terminated = Project(name="Terminated", status=ProjectStatus.TERMINATED)
    session.add(project_terminated)
    session.commit()
    session.refresh(project_terminated)
    
    response_200 = client.delete(f"/projects/{project_terminated.id}")
    assert response_200.headers["content-type"] == "application/json"
    data_200 = response_200.json()
    assert "status" in data_200
    assert "project_id" in data_200


def test_delete_never_returns_500_for_business_logic(client: TestClient, session: Session):
    """DELETE never returns 500 for expected business logic scenarios."""
    # Test all project statuses
    statuses = [
        ProjectStatus.DRAFT,
        ProjectStatus.ACTIVE,
        ProjectStatus.PLANNING,
        ProjectStatus.IN_PROGRESS,
        ProjectStatus.TERMINATING,
    ]
    
    for status in statuses:
        project = Project(name=f"Project {status}", status=status)
        session.add(project)
        session.commit()
        session.refresh(project)
        
        response = client.delete(f"/projects/{project.id}")
        
        # Should return 409, never 500
        assert response.status_code == 409, f"Status {status} returned {response.status_code}"
        assert response.json()["error_code"] == "PROJECT_NOT_TERMINATED"


def test_preflight_options_works(client: TestClient):
    """OPTIONS preflight request works for DELETE."""
    response = client.options(
        "/projects/1",
        headers={
            "Origin": "https://app.blugreen.com.br",
            "Access-Control-Request-Method": "DELETE"
        }
    )
    
    assert response.status_code in [200, 204]
    assert "access-control-allow-methods" in response.headers
    assert "DELETE" in response.headers["access-control-allow-methods"]
