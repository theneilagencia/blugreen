from fastapi.testclient import TestClient


def test_create_task(client: TestClient):
    project_response = client.post("/projects/", json={"name": "Task Test Project"})
    project_id = project_response.json()["id"]

    response = client.post(
        "/tasks/",
        json={
            "title": "Test Task",
            "description": "A test task",
            "task_type": "backend",
            "project_id": project_id,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Task"
    assert data["task_type"] == "backend"
    assert data["status"] == "pending"


def test_list_tasks(client: TestClient):
    project_response = client.post("/projects/", json={"name": "List Tasks Project"})
    project_id = project_response.json()["id"]

    client.post(
        "/tasks/",
        json={"title": "Task 1", "task_type": "backend", "project_id": project_id},
    )
    client.post(
        "/tasks/",
        json={"title": "Task 2", "task_type": "frontend", "project_id": project_id},
    )

    response = client.get("/tasks/", params={"project_id": project_id})
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 2


def test_get_task(client: TestClient):
    project_response = client.post("/projects/", json={"name": "Get Task Project"})
    project_id = project_response.json()["id"]

    create_response = client.post(
        "/tasks/",
        json={"title": "Get Test Task", "task_type": "testing", "project_id": project_id},
    )
    task_id = create_response.json()["id"]

    response = client.get(f"/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "Get Test Task"


def test_update_task(client: TestClient):
    project_response = client.post("/projects/", json={"name": "Update Task Project"})
    project_id = project_response.json()["id"]

    create_response = client.post(
        "/tasks/",
        json={"title": "Update Test", "task_type": "backend", "project_id": project_id},
    )
    task_id = create_response.json()["id"]

    response = client.patch(
        f"/tasks/{task_id}",
        json={"status": "in_progress"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"


def test_delete_task(client: TestClient):
    project_response = client.post("/projects/", json={"name": "Delete Task Project"})
    project_id = project_response.json()["id"]

    create_response = client.post(
        "/tasks/",
        json={"title": "Delete Test", "task_type": "backend", "project_id": project_id},
    )
    task_id = create_response.json()["id"]

    response = client.delete(f"/tasks/{task_id}")
    assert response.status_code == 200

    get_response = client.get(f"/tasks/{task_id}")
    assert get_response.status_code == 404
