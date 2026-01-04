"""
Tests for governed DELETE behavior with explicit blocking and closing flow.

Ensures that:
1. DELETE blocked when project is active (409)
2. DELETE allowed when project is inactive
3. Headers CORS always present
4. No scenario returns 500
5. Close endpoint works correctly
6. Force delete works correctly
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
# Test 1: DELETE blocked when project is active (409)
# ============================================================

def test_delete_project_with_running_workflow_returns_409(client: TestClient, session: Session):
    """DELETE project with running workflow returns 409 Conflict."""
    # Create project
    project = Project(name="Active Project", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create running workflow
    workflow = Workflow(
        name="Running Workflow",
        project_id=project.id,
        status=WorkflowStatus.RUNNING
    )
    session.add(workflow)
    session.commit()

    # Try to delete - should be blocked
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_ACTIVE"
    assert "workflow" in response.json()["message"].lower()


def test_delete_project_with_running_product_returns_409(client: TestClient, session: Session):
    """DELETE project with running product returns 409 Conflict."""
    # Create project
    project = Project(name="Active Project", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create running product
    product = Product(
        name="Running Product",
        project_id=project.id,
        status=ProductStatus.RUNNING
    )
    session.add(product)
    session.commit()

    # Try to delete - should be blocked
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_ACTIVE"
    assert "product" in response.json()["message"].lower()


def test_delete_project_with_running_task_returns_409(client: TestClient, session: Session):
    """DELETE project with running task returns 409 Conflict."""
    # Create project
    project = Project(name="Active Project", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create running task
    task = Task(
        name="Running Task",
        task_type=TaskType.CODE_GENERATION,
        status=TaskStatus.RUNNING,
        project_id=project.id
    )
    session.add(task)
    session.commit()

    # Try to delete - should be blocked
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_ACTIVE"
    assert "task" in response.json()["message"].lower() or "tarefa" in response.json()["message"].lower()


def test_delete_running_project_returns_409(client: TestClient, session: Session):
    """DELETE project with RUNNING status returns 409 Conflict."""
    # Create running project
    project = Project(
        name="Running Project",
        repository_url="https://github.com/test/running",
        status=ProjectStatus.RUNNING
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Try to delete - should be blocked
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 409
    assert response.json()["code"] == "PROJECT_ACTIVE"


# ============================================================
# Test 2: DELETE allowed when project is inactive
# ============================================================

def test_delete_inactive_project_returns_200(client: TestClient, session: Session):
    """DELETE inactive project returns 200."""
    # Create inactive project
    project = Project(
        name="Inactive Project",
        repository_url="https://github.com/test/inactive",
        status=ProjectStatus.DRAFT
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    # Delete should work
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    assert response.json() == {"message": "Project deleted"}


def test_delete_project_with_completed_workflows_returns_200(client: TestClient, session: Session):
    """DELETE project with completed workflows returns 200."""
    # Create project
    project = Project(name="Completed Project", repository_url="https://github.com/test/completed")
    session.add(project)
    session.commit()
    session.refresh(project)

    # Create completed workflow
    workflow = Workflow(
        name="Completed Workflow",
        project_id=project.id,
        status=WorkflowStatus.COMPLETED
    )
    session.add(workflow)
    session.commit()

    # Delete should work
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200


# ============================================================
# Test 3: Headers CORS always present
# ============================================================

def test_delete_409_with_cors_origin_returns_cors_headers(client: TestClient, session: Session):
    """DELETE 409 with Origin header returns CORS headers."""
    # Create project with running workflow
    project = Project(name="Active Project", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="Running", project_id=project.id, status=WorkflowStatus.RUNNING)
    session.add(workflow)
    session.commit()

    # Try to delete with Origin header
    response = client.delete(
        f"/projects/{project.id}",
        headers={"Origin": "https://app.blugreen.com.br"}
    )
    
    assert response.status_code == 409
    assert "access-control-allow-origin" in response.headers


# ============================================================
# Test 4: No scenario returns 500
# ============================================================

def test_delete_never_returns_500(client: TestClient, session: Session):
    """DELETE with any scenario never returns 500."""
    # Create project with all types of active processes
    project = Project(
        name="Complex Active",
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
    
    assert response.status_code != 500
    assert response.status_code == 409


# ============================================================
# Test 5: Close endpoint works correctly
# ============================================================

def test_close_project_stops_active_processes(client: TestClient, session: Session):
    """POST /projects/:id/close stops all active processes."""
    # Create project with active processes
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    product = Product(name="P", project_id=project.id, status=ProductStatus.RUNNING)
    task = Task(name="T", task_type=TaskType.CODE_GENERATION, status=TaskStatus.RUNNING, project_id=project.id)
    
    session.add_all([workflow, product, task])
    session.commit()

    # Close project
    response = client.post(f"/projects/{project.id}/close")
    
    assert response.status_code == 200
    assert response.json()["workflows_stopped"] == 1
    assert response.json()["products_stopped"] == 1
    assert response.json()["tasks_cancelled"] == 1


def test_close_then_delete_succeeds(client: TestClient, session: Session):
    """Close project then delete succeeds."""
    # Create project with active workflow
    project = Project(name="Active", repository_url="https://github.com/test/active")
    session.add(project)
    session.commit()
    session.refresh(project)

    workflow = Workflow(name="W", project_id=project.id, status=WorkflowStatus.RUNNING)
    session.add(workflow)
    session.commit()

    # First, try to delete - should be blocked
    response1 = client.delete(f"/projects/{project.id}")
    assert response1.status_code == 409

    # Close project
    response2 = client.post(f"/projects/{project.id}/close")
    assert response2.status_code == 200

    # Now delete should work
    response3 = client.delete(f"/projects/{project.id}")
    assert response3.status_code == 200


# ============================================================
# Test 6: Force delete works correctly
# ============================================================

def test_force_delete_cancels_active_processes(client: TestClient, session: Session):
    """DELETE with ?force=true cancels active processes and deletes."""
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
    assert response.json() == {"message": "Project deleted"}


def test_force_delete_is_idempotent(client: TestClient, session: Session):
    """Force delete same project twice returns 404 on second attempt."""
    # Create project
    project = Project(name="Test", repository_url="https://github.com/test/test")
    session.add(project)
    session.commit()
    session.refresh(project)

    # First force delete
    response1 = client.delete(f"/projects/{project.id}?force=true")
    assert response1.status_code == 200

    # Second force delete (should return 404)
    response2 = client.delete(f"/projects/{project.id}?force=true")
    assert response2.status_code == 404
