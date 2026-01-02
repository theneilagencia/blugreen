from fastapi.testclient import TestClient


def test_root(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "status" in data
    assert data["status"] == "running"


def test_health(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_create_project(client: TestClient):
    response = client.post(
        "/projects/",
        json={
            "name": "Test Project",
            "description": "A test project",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Test Project"
    assert data["description"] == "A test project"
    assert data["status"] == "draft"
    assert "id" in data


def test_list_projects(client: TestClient):
    client.post("/projects/", json={"name": "Project 1"})
    client.post("/projects/", json={"name": "Project 2"})

    response = client.get("/projects/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_get_project(client: TestClient):
    create_response = client.post("/projects/", json={"name": "Get Test"})
    project_id = create_response.json()["id"]

    response = client.get(f"/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["name"] == "Get Test"


def test_get_project_not_found(client: TestClient):
    response = client.get("/projects/99999")
    assert response.status_code == 404


def test_update_project(client: TestClient):
    create_response = client.post("/projects/", json={"name": "Update Test"})
    project_id = create_response.json()["id"]

    response = client.patch(
        f"/projects/{project_id}",
        json={"name": "Updated Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Name"


def test_delete_project(client: TestClient):
    create_response = client.post("/projects/", json={"name": "Delete Test"})
    project_id = create_response.json()["id"]

    response = client.delete(f"/projects/{project_id}")
    assert response.status_code == 200

    get_response = client.get(f"/projects/{project_id}")
    assert get_response.status_code == 404
