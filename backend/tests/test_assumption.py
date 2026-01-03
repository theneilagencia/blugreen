"""Tests for Assumption API endpoints."""

from fastapi.testclient import TestClient


def test_assume_project(client: TestClient):
    """Test assuming a new project."""
    response = client.post(
        "/assume/project",
        json={
            "name": "Test Assumed Project",
            "description": "A test assumed project",
            "repository_url": "https://github.com/example/repo",
            "branch": "main",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "project_id" in data
    assert "monitor_url" in data


def test_assume_project_default_branch(client: TestClient):
    """Test assuming a project with default branch."""
    response = client.post(
        "/assume/project",
        json={
            "name": "Default Branch Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"


def test_get_assumption_status(client: TestClient):
    """Test getting assumption status."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Status Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "project_name" in data
    assert "assumption_status" in data


def test_get_assumption_status_not_found(client: TestClient):
    """Test getting status for non-existent project."""
    response = client.get("/assume/project/99999/status")
    assert response.status_code == 404


def test_get_project_context_not_found(client: TestClient):
    """Test getting context for non-existent project."""
    response = client.get("/assume/project/99999/context")
    assert response.status_code == 404


def test_get_project_context_not_assumed(client: TestClient):
    """Test getting context for project not yet assumed."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Context Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/context")
    assert response.status_code == 404
    assert "context not found" in response.json()["detail"].lower()


def test_run_diagnostics(client: TestClient):
    """Test running diagnostics on a project."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Diagnostics Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.post(f"/assume/project/{project_id}/diagnostics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "monitor_url" in data


def test_run_diagnostics_not_found(client: TestClient):
    """Test running diagnostics for non-existent project."""
    response = client.post("/assume/project/99999/diagnostics")
    assert response.status_code == 404


def test_get_diagnostics_status(client: TestClient):
    """Test getting diagnostics status."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Diag Status Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/diagnostics/status")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "diagnostics_status" in data


def test_get_diagnostics_status_not_found(client: TestClient):
    """Test getting diagnostics status for non-existent project."""
    response = client.get("/assume/project/99999/diagnostics/status")
    assert response.status_code == 404


def test_get_latest_diagnostics_not_found(client: TestClient):
    """Test getting latest diagnostics for non-existent project."""
    response = client.get("/assume/project/99999/diagnostics/latest")
    assert response.status_code == 404


def test_get_latest_diagnostics_no_results(client: TestClient):
    """Test getting latest diagnostics when none exist."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "No Diag Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/diagnostics/latest")
    assert response.status_code == 404
    assert "no diagnostics found" in response.json()["detail"].lower()


def test_evolve_project(client: TestClient):
    """Test evolving a project."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Evolve Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.post(
        f"/assume/project/{project_id}/evolve",
        json={"change_request": "Add a new feature"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "monitor_url" in data


def test_evolve_project_not_found(client: TestClient):
    """Test evolving non-existent project."""
    response = client.post(
        "/assume/project/99999/evolve",
        json={"change_request": "Add a new feature"},
    )
    assert response.status_code == 404


def test_get_evolution_status(client: TestClient):
    """Test getting evolution status."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Evo Status Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/evolve/status")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "evolution_status" in data


def test_get_evolution_status_not_found(client: TestClient):
    """Test getting evolution status for non-existent project."""
    response = client.get("/assume/project/99999/evolve/status")
    assert response.status_code == 404


def test_get_evolution_history(client: TestClient):
    """Test getting evolution history."""
    create_response = client.post(
        "/assume/project",
        json={
            "name": "Evo History Test Project",
            "repository_url": "https://github.com/example/repo",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/assume/project/{project_id}/evolve/history")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "history" in data


def test_get_evolution_history_not_found(client: TestClient):
    """Test getting evolution history for non-existent project."""
    response = client.get("/assume/project/99999/evolve/history")
    assert response.status_code == 404


def test_rollback_project_not_found(client: TestClient):
    """Test rollback for non-existent project."""
    response = client.post("/assume/project/99999/rollback")
    assert response.status_code == 404
