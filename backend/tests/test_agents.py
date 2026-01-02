from fastapi.testclient import TestClient


def test_list_agents(client: TestClient):
    response = client.get("/agents/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_agent_types(client: TestClient):
    response = client.get("/agents/types")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 7

    agent_types = [a["type"] for a in data]
    assert "architect" in agent_types
    assert "backend" in agent_types
    assert "frontend" in agent_types
    assert "infra" in agent_types
    assert "qa" in agent_types
    assert "ux" in agent_types
    assert "ui_refinement" in agent_types


def test_get_agent(client: TestClient):
    response = client.get("/agents/architect")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_type"] == "architect"


def test_get_agent_capabilities(client: TestClient):
    response = client.get("/agents/architect/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "capabilities" in data
    assert "restrictions" in data
    assert "define_structure" in data["capabilities"]
    assert "never_write_final_code" in data["restrictions"]


def test_backend_agent_capabilities(client: TestClient):
    response = client.get("/agents/backend/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "create_apis" in data["capabilities"]
    assert "never_skip_tests" in data["restrictions"]


def test_frontend_agent_capabilities(client: TestClient):
    response = client.get("/agents/frontend/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "create_functional_ui" in data["capabilities"]
    assert "never_violate_design_system" in data["restrictions"]


def test_qa_agent_capabilities(client: TestClient):
    response = client.get("/agents/qa/capabilities")
    assert response.status_code == 200
    data = response.json()
    assert "run_tests" in data["capabilities"]
    assert "block_deploy" in data["capabilities"]
    assert "never_approve_without_tests" in data["restrictions"]
