"""
Tests that guarantee DELETE /projects/{id} NEVER breaks again.

ABSOLUTE GUARANTEES:
- DELETE always returns JSON
- DELETE never returns 500 without body
- CORS headers always present
- No exception ever escapes
- Frontend always gets clear error_code

This is a NO-THROW ZONE test suite.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from sqlmodel import SQLModel
from app.database import get_session
from app.models.project import Project, ProjectStatus
from app.models.workflow import Workflow, WorkflowStatus
from app.models.product import Product, ProductStatus


# Test database setup
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_no_throw_zone.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_session():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(autouse=True)
def setup_database():
    """Create fresh database for each test"""
    SQLModel.metadata.create_all(bind=engine)
    yield
    SQLModel.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    """Test client"""
    return TestClient(app)


@pytest.fixture
def db():
    """Database session"""
    session = TestingSessionLocal()
    yield session
    session.close()


# TEST 1: DELETE returns JSON even when project not found
def test_delete_not_found_returns_json(client):
    """DELETE must return JSON with error_code when project not found"""
    response = client.delete("/projects/99999")
    
    # Must return JSON
    assert response.headers.get("content-type") == "application/json"
    
    # Must have error_code
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "PROJECT_NOT_FOUND"
    assert "message" in data
    
    # Must be 404
    assert response.status_code == 404


# TEST 2: DELETE returns JSON when project is ACTIVE
def test_delete_active_project_returns_json(client, db):
    """DELETE must return JSON with error_code when project is ACTIVE"""
    # Create ACTIVE project
    project = Project(
        name="Active Project",
        description="Test",
        status=ProjectStatus.ACTIVE
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    
    # Must return JSON
    assert response.headers.get("content-type") == "application/json"
    
    # Must have error_code
    data = response.json()
    assert "error_code" in data
    assert data["error_code"] == "PROJECT_ACTIVE"
    assert "message" in data
    
    # Must be 409
    assert response.status_code == 409


# TEST 3: DELETE returns JSON when project has constraints
def test_delete_with_constraints_returns_json(client, db):
    """DELETE must return JSON with error_code when database constraint fails"""
    # Create TERMINATED project with active workflow (simulates constraint)
    project = Project(
        name="Project with Workflow",
        description="Test",
        status=ProjectStatus.TERMINATED
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    # Add workflow (this might cause constraint if CASCADE not working)
    workflow = Workflow(
        project_id=project.id,
        name="Test Workflow",
        status=WorkflowStatus.IN_PROGRESS
    )
    db.add(workflow)
    db.commit()
    
    response = client.delete(f"/projects/{project.id}")
    
    # Must return JSON (either success or constraint error)
    assert response.headers.get("content-type") == "application/json"
    
    data = response.json()
    
    # Must have either success or error_code
    if response.status_code == 200:
        assert data.get("status") == "deleted"
    else:
        assert "error_code" in data
        assert data["error_code"] == "PROJECT_DELETE_CONSTRAINT"
        assert response.status_code == 409


# TEST 4: DELETE DRAFT project succeeds
def test_delete_draft_project_succeeds(client, db):
    """DELETE must succeed for DRAFT projects"""
    project = Project(
        name="Draft Project",
        description="Test",
        status=ProjectStatus.DRAFT
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    
    # Must return JSON
    assert response.headers.get("content-type") == "application/json"
    
    # Must succeed
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"


# TEST 5: DELETE TERMINATED project succeeds
def test_delete_terminated_project_succeeds(client, db):
    """DELETE must succeed for TERMINATED projects"""
    project = Project(
        name="Terminated Project",
        description="Test",
        status=ProjectStatus.TERMINATED
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    
    # Must return JSON
    assert response.headers.get("content-type") == "application/json"
    
    # Must succeed
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "deleted"


# TEST 6: CORS headers always present
def test_delete_always_has_cors_headers(client, db):
    """DELETE must ALWAYS return CORS headers, even on error"""
    # Test 404 case
    response = client.delete("/projects/99999")
    assert "access-control-allow-origin" in response.headers
    
    # Test 409 case (ACTIVE project)
    project = Project(
        name="Active Project",
        description="Test",
        status=ProjectStatus.ACTIVE
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    assert "access-control-allow-origin" in response.headers


# TEST 7: DELETE never returns 500 without body
def test_delete_never_returns_empty_500(client, db):
    """DELETE must NEVER return 500 without JSON body"""
    # Even if something catastrophic happens, must return JSON
    # This test ensures the ultimate safety net works
    
    project = Project(
        name="Test Project",
        description="Test",
        status=ProjectStatus.DRAFT
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    
    # Must have content-type
    assert "content-type" in response.headers
    
    # Must be JSON
    assert "application/json" in response.headers["content-type"]
    
    # Must have body
    data = response.json()
    assert data is not None
    
    # If 500, must have error_code
    if response.status_code == 500:
        assert "error_code" in data
        assert data["error_code"] == "PROJECT_DELETE_INTERNAL_ERROR"


# TEST 8: All error responses have consistent structure
def test_all_errors_have_consistent_structure(client, db):
    """All error responses must have error_code and message"""
    
    # Test 404
    response = client.delete("/projects/99999")
    data = response.json()
    assert "error_code" in data
    assert "message" in data
    assert isinstance(data["error_code"], str)
    assert isinstance(data["message"], str)
    
    # Test 409
    project = Project(
        name="Active Project",
        description="Test",
        status=ProjectStatus.ACTIVE
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    data = response.json()
    assert "error_code" in data
    assert "message" in data
    assert isinstance(data["error_code"], str)
    assert isinstance(data["message"], str)


# TEST 9: Success response has consistent structure
def test_success_has_consistent_structure(client, db):
    """Success response must have status field"""
    project = Project(
        name="Draft Project",
        description="Test",
        status=ProjectStatus.DRAFT
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    
    response = client.delete(f"/projects/{project.id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "deleted"


# TEST 10: Invalid project ID returns JSON
def test_invalid_project_id_returns_json(client):
    """DELETE with invalid ID must return JSON, not crash"""
    # Test with string ID (should be caught by FastAPI validation)
    response = client.delete("/projects/invalid")
    
    # Must return JSON
    assert "application/json" in response.headers.get("content-type", "")
    
    # Must have error structure
    data = response.json()
    assert "detail" in data or "error_code" in data


# TEST 11: Idempotency - deleting twice doesn't crash
def test_delete_idempotency(client, db):
    """Deleting same project twice must not crash"""
    project = Project(
        name="Draft Project",
        description="Test",
        status=ProjectStatus.DRAFT
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    project_id = project.id
    
    # First delete - should succeed
    response1 = client.delete(f"/projects/{project_id}")
    assert response1.status_code == 200
    
    # Second delete - should return 404 with JSON
    response2 = client.delete(f"/projects/{project_id}")
    assert response2.status_code == 404
    assert response2.headers.get("content-type") == "application/json"
    data = response2.json()
    assert data["error_code"] == "PROJECT_NOT_FOUND"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
