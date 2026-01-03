"""Tests for Product API endpoints."""

from fastapi.testclient import TestClient


def test_create_product(client: TestClient):
    """Test creating a new product."""
    response = client.post(
        "/product/create",
        json={
            "name": "Test Product",
            "description": "A test product",
            "requirements": "Build a simple todo app",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "started"
    assert "project_id" in data
    assert "monitor_url" in data


def test_get_product_status(client: TestClient):
    """Test getting product creation status."""
    create_response = client.post(
        "/product/create",
        json={
            "name": "Status Test Product",
            "description": "Testing status endpoint",
            "requirements": "Build a simple app",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/product/{project_id}/status")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "project_name" in data
    assert "project_status" in data
    assert "creation_status" in data


def test_get_product_status_not_found(client: TestClient):
    """Test getting status for non-existent product."""
    response = client.get("/product/99999/status")
    assert response.status_code == 404


def test_deploy_product_not_found(client: TestClient):
    """Test deploying non-existent product."""
    response = client.post(
        "/product/99999/deploy",
        json={
            "docker_image": "test:latest",
        },
    )
    assert response.status_code == 404


def test_deploy_product_wrong_status(client: TestClient):
    """Test deploying product with wrong status."""
    create_response = client.post(
        "/product/create",
        json={
            "name": "Deploy Test Product",
            "description": "Testing deploy endpoint",
            "requirements": "Build a simple app",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.post(
        f"/product/{project_id}/deploy",
        json={
            "docker_image": "test:latest",
        },
    )
    assert response.status_code == 400
    assert "status" in response.json()["detail"].lower()


def test_rollback_product_not_found(client: TestClient):
    """Test rollback for non-existent product."""
    response = client.post("/product/99999/rollback")
    assert response.status_code == 404


def test_get_deployment_status_not_found(client: TestClient):
    """Test getting deployment status for non-existent product."""
    response = client.get("/product/99999/deployment/status")
    assert response.status_code == 404


def test_get_deployment_history_not_found(client: TestClient):
    """Test getting deployment history for non-existent product."""
    response = client.get("/product/99999/deployment/history")
    assert response.status_code == 404


def test_get_deployment_history(client: TestClient):
    """Test getting deployment history for existing product."""
    create_response = client.post(
        "/product/create",
        json={
            "name": "History Test Product",
            "description": "Testing history endpoint",
            "requirements": "Build a simple app",
        },
    )
    project_id = create_response.json()["project_id"]

    response = client.get(f"/product/{project_id}/deployment/history")
    assert response.status_code == 200
    data = response.json()
    assert data["project_id"] == project_id
    assert "deployments" in data
