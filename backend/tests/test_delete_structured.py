"""
Tests for DELETE /projects/:id with structured responses.

Ensures that:
1. DELETE with dependencies returns 409 with structured response
2. DELETE without dependencies returns 200
3. DELETE repeated returns 404 (idempotent)
4. DELETE never returns 500 for business rules
5. Headers CORS always present
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models.project import Project, ProjectStatus
from app.models.product import Product, ProductStatus
from app.models.workflow import Workflow, WorkflowStatus
from app.models.task import Task, TaskType, TaskStatus


# Test database setup
@pytest.fixture(name="session")
def session_fixture():
    """Create in-memory SQLite database for testing."""
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
    """Create test client with overridden database session."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


# ============================================================
# Test 1: DELETE with dependencies returns 409 with structured response
# ============================================================

def test_delete_with_active_workflow_returns_409_structured(client: TestClient, session: Session):
    """DELETE with active workflow returns 409 with structured response."""
    # Create project with active workflow
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    session.add(workflow)
    session.commit()

    # Try to delete
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    data = response.json()
    
    # Validate structured response
    assert data["error_code"] == "PROJECT_HAS_ACTIVE_DEPENDENCIES"
    assert "message" in data
    assert "details" in data
    assert isinstance(data["details"], list)
    assert len(data["details"]) > 0
    assert "action" in data
    assert "workflow" in str(data["details"]).lower()


def test_delete_with_active_product_returns_409_structured(client: TestClient, session: Session):
    """DELETE with active product returns 409 with structured response."""
    # Create project with active product
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    product = Product(name="P", project_id=project.id, status=ProductStatus.RUNNING)
    session.add(product)
    session.commit()

    # Try to delete
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    data = response.json()
    
    assert data["error_code"] == "PROJECT_HAS_ACTIVE_DEPENDENCIES"
    assert "produto" in str(data["details"]).lower()


def test_delete_with_active_task_returns_409_structured(client: TestClient, session: Session):
    """DELETE with active task returns 409 with structured response."""
    # Create project with active task
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    task = Task(
        name="T",
        task_type=TaskType.CODE_GENERATION,
        status=TaskStatus.RUNNING,
        project_id=project.id
    )
    session.add(task)
    session.commit()

    # Try to delete
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    data = response.json()
    
    assert data["error_code"] == "PROJECT_HAS_ACTIVE_DEPENDENCIES"
    assert "tarefa" in str(data["details"]).lower()


def test_delete_running_project_returns_409_structured(client: TestClient, session: Session):
    """DELETE running project returns 409 with structured response."""
    # Create running project
    project = Project(
        name="Running",
        repository_url="https://github.com/test/running",
        status=ProjectStatus.RUNNING
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Try to delete
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    data = response.json()
    
    assert data["error_code"] == "PROJECT_HAS_ACTIVE_DEPENDENCIES"
    assert "execução" in str(data["details"]).lower()


# ============================================================
# Test 2: DELETE without dependencies returns 200
# ============================================================

def test_delete_inactive_project_returns_200_structured(client: TestClient, session: Session):
    """DELETE inactive project returns 200 with structured response."""
    # Create inactive project
    project = Project(
        name="Inactive",
        repository_url="https://github.com/test/inactive",
        status=ProjectStatus.DRAFT
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Delete should work
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    # Validate structured response
    assert data["status"] == "deleted"
    assert data["project_id"] == project.id


def test_delete_project_with_completed_workflows_returns_200(client: TestClient, session: Session):
    """DELETE project with completed workflows returns 200."""
    # Create project with completed workflow
    project = Project(name="Completed", repository_url="https://github.com/test/completed")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.COMPLETED)
    session.add(workflow)
    session.commit()

    # Delete should work
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"


# ============================================================
# Test 3: DELETE repeated returns 404 (idempotent)
# ============================================================

def test_delete_repeated_returns_404(client: TestClient, session: Session):
    """DELETE same project twice returns 404 on second attempt."""
    # Create project
    project = Project(name="Test", repository_url="https://github.com/test/test")
    session.add(project)
    session.commit()
    session.refresh(project)
    project_id = project.id

    # First delete
    response1 = client.delete(f"/projects/{project_id}")
    assert response1.status_code == 200

    # Second delete (should return 404)
    response2 = client.delete(f"/projects/{project_id}")
    assert response2.status_code == 404
    
    data = response2.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"


def test_delete_nonexistent_project_returns_404(client: TestClient, session: Session):
    """DELETE non-existent project returns 404."""
    response = client.delete("/projects/99999")
    
    assert response.status_code == 404
    data = response.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"


# ============================================================
# Test 4: DELETE never returns 500 for business rules
# ============================================================

def test_delete_with_multiple_dependencies_returns_409_not_500(client: TestClient, session: Session):
    """DELETE with multiple dependencies returns 409, not 500."""
    # Create project with all types of dependencies
    project = Project(
        name="Complex",
        repository_url="https://github.com/test/complex",
        status=ProjectStatus.RUNNING
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    product = Product(name="P", project_id=project.id, status=ProductStatus.RUNNING)
    task = Task(name="T", task_type=TaskType.CODE_GENERATION, status=TaskStatus.RUNNING, project_id=project.id)
    
    session.add_all([workflow, product, task])
    session.commit()

    # Try to delete - should return 409, not 500
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    assert response.status_code != 500
    
    data = response.json()
    assert data["error_code"] == "PROJECT_HAS_ACTIVE_DEPENDENCIES"
    assert len(data["details"]) >= 3  # Should list all 3+ dependencies


# ============================================================
# Test 5: Headers CORS always present
# ============================================================

def test_delete_409_with_origin_returns_cors_headers(client: TestClient, session: Session):
    """DELETE 409 with Origin header returns CORS headers."""
    # Create project with active workflow
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    session.add(workflow)
    session.commit()

    # Try to delete with Origin header
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 409
    assert "access-control-allow-origin" in response.headers


def test_delete_404_with_origin_returns_cors_headers(client: TestClient, session: Session):
    """DELETE 404 with Origin header returns CORS headers."""
    response = client.delete(
        "/projects/99999",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 404
    assert "access-control-allow-origin" in response.headers


def test_delete_200_with_origin_returns_cors_headers(client: TestClient, session: Session):
    """DELETE 200 with Origin header returns CORS headers."""
    # Create project
    project = Project(name="Test", repository_url="https://github.com/test/test")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Delete with Origin header
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 200
    assert "access-control-allow-origin" in response.headers


# ============================================================
# Test 6: Force delete works correctly
# ============================================================

def test_force_delete_with_dependencies_returns_200(client: TestClient, session: Session):
    """DELETE with ?force=true cancels dependencies and deletes."""
    # Create project with active workflow
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    session.add(workflow)
    session.commit()

    # Force delete
    response = client.delete(f"/projects/{project.id}?force=true")
    
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
