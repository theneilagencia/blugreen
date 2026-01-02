from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class BackendAgent(BaseAgent):
    agent_type = AgentType.BACKEND
    capabilities = [
        "create_apis",
        "model_database",
        "write_tests",
        "implement_business_logic",
        "create_endpoints",
    ]
    restrictions = [
        "never_modify_frontend",
        "never_change_infrastructure",
        "never_skip_tests",
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.BACKEND, TaskType.TESTING]:
            return False, f"Backend agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type in [TaskType.BACKEND, TaskType.TESTING]

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            if task.task_type == TaskType.BACKEND:
                result = await self._implement_backend(task)
            else:
                result = await self._write_tests(task)

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

    async def _implement_backend(self, task: Task) -> dict[str, Any]:
        return {
            "type": "backend_implementation",
            "components": [
                "api_routes",
                "database_models",
                "business_logic",
                "validation",
            ],
            "endpoints_created": [],
            "models_created": [],
        }

    async def _write_tests(self, task: Task) -> dict[str, Any]:
        return {
            "type": "test_implementation",
            "test_types": [
                "unit_tests",
                "integration_tests",
                "api_tests",
            ],
            "tests_created": [],
            "coverage": 0.0,
        }
