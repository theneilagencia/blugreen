from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class FrontendAgent(BaseAgent):
    agent_type = AgentType.FRONTEND
    capabilities = [
        "create_functional_ui",
        "implement_components",
        "connect_to_api",
        "handle_state",
        "implement_routing",
    ]
    restrictions = [
        "never_create_complex_design",
        "never_modify_backend",
        "never_violate_design_system",
        "only_use_allowed_components",
    ]

    ALLOWED_COMPONENTS = [
        "Button",
        "Input",
        "Select",
        "Modal",
        "Table",
        "Card",
        "Alert",
        "Badge",
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.FRONTEND]:
            return False, f"Frontend agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.FRONTEND

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._implement_frontend(task)
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

    async def _implement_frontend(self, task: Task) -> dict[str, Any]:
        return {
            "type": "frontend_implementation",
            "components_used": self.ALLOWED_COMPONENTS,
            "pages_created": [],
            "api_connections": [],
            "design_system_compliance": True,
        }

    def validate_component_usage(self, components: list[str]) -> tuple[bool, list[str]]:
        invalid_components = [c for c in components if c not in self.ALLOWED_COMPONENTS]
        return len(invalid_components) == 0, invalid_components
