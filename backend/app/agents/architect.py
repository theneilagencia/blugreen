from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class ArchitectAgent(BaseAgent):
    agent_type = AgentType.ARCHITECT
    capabilities = [
        "define_structure",
        "create_boundaries",
        "design_architecture",
        "plan_modules",
        "define_contracts",
    ]
    restrictions = [
        "never_write_final_code",
        "never_implement_features",
        "never_modify_existing_code",
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.PLANNING]:
            return False, f"Architect agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.PLANNING

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._design_architecture(task)
            self.complete_task(task, success=True)
            return {
                "status": "success",
                "architecture": result,
            }
        except Exception as e:
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _design_architecture(self, task: Task) -> dict[str, Any]:
        return {
            "layers": [
                {
                    "name": "user_interface",
                    "description": "Web interface with task-oriented chat",
                    "technology": "Next.js + Tailwind CSS",
                },
                {
                    "name": "orchestrator",
                    "description": "Central planning and state management",
                    "technology": "FastAPI",
                },
                {
                    "name": "agents",
                    "description": "Specialized agents for different tasks",
                    "technology": "Python",
                },
                {
                    "name": "executor",
                    "description": "Code execution, tests, build, sandbox",
                    "technology": "Docker",
                },
                {
                    "name": "cicd",
                    "description": "Build, tests, deploy, rollback",
                    "technology": "Self-hosted CI + Coolify",
                },
            ],
            "boundaries": [
                "No layer accesses another without explicit contract",
                "All communication through defined APIs",
                "State changes must be explicit",
            ],
            "contracts": [
                {
                    "from": "user_interface",
                    "to": "orchestrator",
                    "type": "REST API",
                },
                {
                    "from": "orchestrator",
                    "to": "agents",
                    "type": "Internal API",
                },
                {
                    "from": "agents",
                    "to": "executor",
                    "type": "Command execution",
                },
            ],
        }
