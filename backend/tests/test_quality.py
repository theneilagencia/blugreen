from fastapi.testclient import TestClient


def test_get_ux_rules(client: TestClient):
    response = client.get("/quality/ux/rules")
    assert response.status_code == 200
    data = response.json()
    assert "rules" in data
    assert "criteria" in data
    assert "threshold" in data
    assert len(data["rules"]) == 5


def test_evaluate_ux(client: TestClient):
    response = client.post("/quality/ux/evaluate", json={})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "recommendations" in data
    assert "can_proceed" in data


def test_get_design_system(client: TestClient):
    response = client.get("/quality/ui/design-system")
    assert response.status_code == 200
    data = response.json()
    assert "tokens" in data
    assert "allowed_components" in data
    assert "criteria" in data

    assert "spacing" in data["tokens"]
    assert data["tokens"]["spacing"]["xs"] == 4
    assert data["tokens"]["spacing"]["sm"] == 8
    assert data["tokens"]["spacing"]["md"] == 16
    assert data["tokens"]["spacing"]["lg"] == 24
    assert data["tokens"]["spacing"]["xl"] == 32

    assert "Button" in data["allowed_components"]
    assert "Input" in data["allowed_components"]
    assert "Modal" in data["allowed_components"]


def test_evaluate_ui(client: TestClient):
    response = client.post("/quality/ui/evaluate", json={})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert "recommendations" in data
    assert "can_proceed" in data


def test_check_deploy_readiness_all_passed(client: TestClient):
    response = client.post(
        "/quality/deploy/check",
        params={
            "tests_passed": True,
            "ux_approved": True,
            "ui_approved": True,
            "security_passed": True,
            "build_successful": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["can_deploy"] is True


def test_check_deploy_readiness_tests_failed(client: TestClient):
    response = client.post(
        "/quality/deploy/check",
        params={
            "tests_passed": False,
            "ux_approved": True,
            "ui_approved": True,
            "security_passed": True,
            "build_successful": True,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["can_deploy"] is False
    assert len(data["blocking_issues"]) > 0


def test_get_deploy_requirements(client: TestClient):
    response = client.get("/quality/deploy/requirements")
    assert response.status_code == 200
    data = response.json()
    assert "required_checks" in data
    assert len(data["required_checks"]) == 5
    assert data["force_deploy_allowed"] is False
