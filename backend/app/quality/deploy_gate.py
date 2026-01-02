from typing import Any, Optional


class DeployGate:
    REQUIRED_CHECKS = [
        {
            "id": "tests_passed",
            "name": "All Tests Passed",
            "required": True,
        },
        {
            "id": "ux_approved",
            "name": "UX Quality Approved",
            "required": True,
        },
        {
            "id": "ui_approved",
            "name": "UI Quality Approved",
            "required": True,
        },
        {
            "id": "no_security_issues",
            "name": "No Security Issues",
            "required": True,
        },
        {
            "id": "build_successful",
            "name": "Build Successful",
            "required": True,
        },
    ]

    def __init__(self) -> None:
        self.results: dict[str, Any] = {}
        self.check_results: dict[str, bool] = {}

    def run_checks(
        self,
        tests_passed: bool = False,
        ux_approved: bool = False,
        ui_approved: bool = False,
        security_passed: bool = False,
        build_successful: bool = False,
    ) -> dict[str, Any]:
        self.check_results = {
            "tests_passed": tests_passed,
            "ux_approved": ux_approved,
            "ui_approved": ui_approved,
            "no_security_issues": security_passed,
            "build_successful": build_successful,
        }

        check_details = []
        all_passed = True

        for check in self.REQUIRED_CHECKS:
            passed = self.check_results.get(check["id"], False)
            check_details.append({
                "check_id": check["id"],
                "check_name": check["name"],
                "passed": passed,
                "required": check["required"],
            })
            if check["required"] and not passed:
                all_passed = False

        self.results = {
            "can_deploy": all_passed,
            "checks": check_details,
            "failed_checks": [c for c in check_details if not c["passed"]],
        }

        return self.results

    def can_deploy(self) -> tuple[bool, Optional[str]]:
        if not self.results:
            return False, "Checks not run"

        if self.results.get("can_deploy", False):
            return True, None

        failed = self.results.get("failed_checks", [])
        if failed:
            failed_names = [c["check_name"] for c in failed]
            return False, f"Deploy blocked: {', '.join(failed_names)}"

        return False, "Deploy blocked: unknown reason"

    def get_blocking_issues(self) -> list[str]:
        if not self.results:
            return ["Checks not run"]

        issues = []
        for check in self.results.get("failed_checks", []):
            issues.append(f"{check['check_name']} failed")

        return issues

    def force_deploy_allowed(self) -> bool:
        return False

    def get_rollback_plan(self) -> dict[str, Any]:
        return {
            "steps": [
                "Identify the issue",
                "Revert to previous version",
                "Run healthcheck",
                "Verify rollback successful",
                "Notify stakeholders",
            ],
            "automatic": True,
            "trigger": "healthcheck_failure",
        }
