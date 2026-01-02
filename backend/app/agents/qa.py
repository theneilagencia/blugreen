from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class QAAgent(BaseAgent):
    agent_type = AgentType.QA
    capabilities = [
        "run_tests",
        "break_system",
        "validate_quality",
        "block_deploy",
        "report_issues",
    ]
    restrictions = [
        "never_approve_without_tests",
        "never_skip_validation",
        "never_ignore_failures",
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.TESTING]:
            return False, f"QA agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.TESTING

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._run_quality_checks(task)

            if not result["all_passed"]:
                self.complete_task(task, success=False, error_message="Quality checks failed")
                return {
                    "status": "blocked",
                    "result": result,
                    "message": "Deploy blocked due to quality failures",
                }

            self.complete_task(task, success=True)
            return {
                "status": "success",
                "result": result,
            }
        except Exception as e:
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _run_quality_checks(self, task: Task) -> dict[str, Any]:
        test_results = await self._run_tests()
        security_results = await self._run_security_checks()
        performance_results = await self._run_performance_checks()

        all_passed = (
            test_results["passed"]
            and security_results["passed"]
            and performance_results["passed"]
        )

        return {
            "all_passed": all_passed,
            "tests": test_results,
            "security": security_results,
            "performance": performance_results,
        }

    async def _run_tests(self) -> dict[str, Any]:
        return {
            "passed": True,
            "total": 0,
            "passed_count": 0,
            "failed_count": 0,
            "coverage": 0.0,
        }

    async def _run_security_checks(self) -> dict[str, Any]:
        return {
            "passed": True,
            "vulnerabilities": [],
            "warnings": [],
        }

    async def _run_performance_checks(self) -> dict[str, Any]:
        return {
            "passed": True,
            "metrics": {},
        }

    def can_deploy(self, quality_results: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if not quality_results.get("all_passed", False):
            failures = []
            if not quality_results.get("tests", {}).get("passed", False):
                failures.append("Tests failed")
            if not quality_results.get("security", {}).get("passed", False):
                failures.append("Security checks failed")
            if not quality_results.get("performance", {}).get("passed", False):
                failures.append("Performance checks failed")
            return False, "; ".join(failures)
        return True, None
