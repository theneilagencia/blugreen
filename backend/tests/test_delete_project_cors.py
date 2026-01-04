"""
Tests for DELETE /projects/:id endpoint with CORS validation.

Ensures that:
1. DELETE never returns 500 (IntegrityError)
2. CORS headers are always present
3. DELETE is idempotent
4. Projects with deep dependencies are removed correctly
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, create_engine, SQLModel
from sqlmodel.pool import StaticPool

from app.main import app
from app.database import get_session
from app.models.project import Project
from app.models.product import Product
from app.models.workflow import Workflow
from app.models.task import Task, TaskType, TaskStatus
from app.models.project_agent import ProjectAgent, ProjectAgentRole
from app.models.quality_metric import QualityMetric, MetricCategory


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
# Test 1: DELETE never returns 500
# ============================================================

def test_delete_project_without_dependencies_returns_200(client: TestClient, session: Session):
    """DELETE project without dependencies returns 200."""
    # Create project
    project = Project(name="Test Project", repository_url="https://github.com/test/repo")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Delete project
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Project deleted"}


def test_delete_project_with_deep_dependencies_returns_200(client: TestClient, session: Session):
    """DELETE project with workflows, tasks, products returns 200 (CASCADE)."""
    # Create project
    project = Project(name="Complex Project", repository_url="https://github.com/test/complex")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create dependencies
    workflow = Workflow(name="Test Workflow", project_id=project.id)
    session.add(workflow)
    
    task = Task(
        name="Test Task",
        task_type=TaskType.CODE_GENERATION,
        status=TaskStatus.PENDING,
        project_id=project.id
    )
    session.add(task)
    
    product = Product(name="Test Product", project_id=project.id)
    session.add(product)
    
    session.commit()

    # Delete project - should CASCADE delete all dependencies
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Project deleted"}
    
    # Verify dependencies were deleted
    assert session.get(Workflow, workflow.id) is None
    assert session.get(Task, task.id) is None
    assert session.get(Product, product.id) is None


def test_delete_nonexistent_project_returns_404(client: TestClient):
    """DELETE non-existent project returns 404."""
    response = client.delete("/projects/99999")
    
    assert response.status_code == 404
    assert response.json() == {"detail": "Project not found"}


# ============================================================
# Test 2: CORS headers always present
# ============================================================

def test_delete_with_cors_origin_returns_cors_headers(client: TestClient, session: Session):
    """DELETE with Origin header returns CORS headers."""
    # Create project
    project = Project(name="CORS Test", repository_url="https://github.com/test/cors")
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
    assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"
    assert "access-control-allow-credentials" in response.headers


def test_delete_404_with_cors_origin_returns_cors_headers(client: TestClient):
    """DELETE 404 with Origin header returns CORS headers."""
    response = client.delete(
        "/projects/99999",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 404
    assert "access-control-allow-origin" in response.headers
    assert response.headers["access-control-allow-origin"] == "https://app.blugreen.com.br"


def test_options_preflight_returns_cors_headers(client: TestClient):
    """OPTIONS preflight for DELETE returns CORS headers."""
    response = client.options(
        "/projects/1",
        headers={
            "Origin": "https://app.blugreen.com.br",
            "Access-Control-Request-Method": "DELETE"
        }
    )
    
    assert response.status_code in [200, 204]
    assert "access-control-allow-origin" in response.headers
    assert "access-control-allow-methods" in response.headers
    assert "DELETE" in response.headers["access-control-allow-methods"]


# ============================================================
# Test 3: DELETE is idempotent
# ============================================================

def test_delete_is_idempotent(client: TestClient, session: Session):
    """DELETE same project twice returns 404 on second attempt."""
    # Create project
    project = Project(name="Idempotent Test", repository_url="https://github.com/test/idempotent")
    session.add(project)
    session.commit()
    session.refresh(project)

    # First delete
    response1 = client.delete(f"/projects/{project.id}")
    assert response1.status_code == 200

    # Second delete (should return 404)
    response2 = client.delete(f"/projects/{project.id}")
    assert response2.status_code == 404


# ============================================================
# Test 4: No IntegrityError (regression test)
# ============================================================

def test_delete_never_returns_500_integrity_error(client: TestClient, session: Session):
    """DELETE with all possible dependencies never returns 500."""
    # Create project with ALL types of dependencies
    project = Project(name="Full Dependencies", repository_url="https://github.com/test/full")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Add all types of dependencies
    workflow = Workflow(name="Workflow", project_id=project.id)
    task = Task(name="Task", task_type=TaskType.CODE_GENERATION, status=TaskStatus.PENDING, project_id=project.id)
    product = Product(name="Product", project_id=project.id)
    
    session.add_all([workflow, task, product])
    session.commit()

    # Delete should work without IntegrityError
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code != 500
    assert response.status_code == 200
    assert "IntegrityError" not in response.text


# ============================================================
# Test 5: Validate CASCADE behavior
# ============================================================

def test_cascade_delete_removes_all_related_records(client: TestClient, session: Session):
    """CASCADE delete removes all related records automatically."""
    # Create project
    project = Project(name="CASCADE Test", repository_url="https://github.com/test/cascade")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create multiple dependencies
    workflows = [Workflow(name=f"Workflow {i}", project_id=project.id) for i in range(3)]
    tasks = [Task(name=f"Task {i}", task_type=TaskType.CODE_GENERATION, status=TaskStatus.PENDING, project_id=project.id) for i in range(3)]
    products = [Product(name=f"Product {i}", project_id=project.id) for i in range(3)]
    
    session.add_all(workflows + tasks + products)
    session.commit()

    # Get IDs before delete
    workflow_ids = [w.id for w in workflows]
    task_ids = [t.id for t in tasks]
    product_ids = [p.id for p in products]

    # Delete project
    response = client.delete(f"/projects/{project.id}")
    assert response.status_code == 200

    # Verify ALL dependencies were deleted
    for wid in workflow_ids:
        assert session.get(Workflow, wid) is None
    for tid in task_ids:
        assert session.get(Task, tid) is None
    for pid in product_ids:
        assert session.get(Product, pid) is None
