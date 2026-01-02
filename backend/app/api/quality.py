from fastapi import APIRouter

from app.quality import DeployGate, UIQualityGate, UXQualityGate

router = APIRouter(prefix="/quality", tags=["quality"])


@router.get("/ux/rules")
def get_ux_rules() -> dict:
    gate = UXQualityGate()
    return {
        "rules": gate.UX_RULES,
        "criteria": gate.CRITERIA,
        "threshold": gate.PASSING_THRESHOLD,
    }


@router.post("/ux/evaluate")
def evaluate_ux(ux_data: dict) -> dict:
    gate = UXQualityGate()
    results = gate.evaluate(ux_data)
    recommendations = gate.get_recommendations()
    can_proceed, message = gate.can_proceed()

    return {
        "results": results,
        "recommendations": recommendations,
        "can_proceed": can_proceed,
        "message": message,
    }


@router.get("/ui/design-system")
def get_design_system() -> dict:
    gate = UIQualityGate()
    return {
        "tokens": gate.get_design_tokens(),
        "allowed_components": gate.get_allowed_components(),
        "criteria": gate.CRITERIA,
        "threshold": gate.PASSING_THRESHOLD,
    }


@router.post("/ui/evaluate")
def evaluate_ui(ui_data: dict) -> dict:
    gate = UIQualityGate()
    results = gate.evaluate(ui_data)
    recommendations = gate.get_recommendations()
    can_proceed, message = gate.can_proceed()

    return {
        "results": results,
        "recommendations": recommendations,
        "can_proceed": can_proceed,
        "message": message,
    }


@router.post("/deploy/check")
def check_deploy_readiness(
    tests_passed: bool = False,
    ux_approved: bool = False,
    ui_approved: bool = False,
    security_passed: bool = False,
    build_successful: bool = False,
) -> dict:
    gate = DeployGate()
    results = gate.run_checks(
        tests_passed=tests_passed,
        ux_approved=ux_approved,
        ui_approved=ui_approved,
        security_passed=security_passed,
        build_successful=build_successful,
    )

    can_deploy, message = gate.can_deploy()
    blocking_issues = gate.get_blocking_issues()
    rollback_plan = gate.get_rollback_plan()

    return {
        "results": results,
        "can_deploy": can_deploy,
        "message": message,
        "blocking_issues": blocking_issues,
        "rollback_plan": rollback_plan,
    }


@router.get("/deploy/requirements")
def get_deploy_requirements() -> dict:
    gate = DeployGate()
    return {
        "required_checks": gate.REQUIRED_CHECKS,
        "force_deploy_allowed": gate.force_deploy_allowed(),
    }
