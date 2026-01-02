from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType


class InfraAgent(BaseAgent):
    agent_type = AgentType.INFRA
    capabilities = [
        "create_docker_config",
        "setup_cicd",
        "configure_deployment",
        "manage_environments",
        "setup_monitoring",
    ]
    restrictions = [
        "never_use_paid_services",
        "never_expose_secrets",
        "never_execute_destructive_commands",
        "never_hardcode_env_vars",
    ]

    FORBIDDEN_COMMANDS = [
        "rm -rf",
        "rm -r /",
        "dd if=",
        "mkfs",
        "> /dev/sda",
        "chmod -R 777",
    ]

    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        if task.task_type not in [TaskType.DEPLOYMENT]:
            return False, f"Infra agent cannot handle task type: {task.task_type}"
        return True, None

    def can_handle_task(self, task: Task) -> bool:
        return task.task_type == TaskType.DEPLOYMENT

    async def execute(self, task: Task) -> dict[str, Any]:
        self.assign_task(task)

        try:
            result = await self._setup_infrastructure(task)
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

    async def _setup_infrastructure(self, task: Task) -> dict[str, Any]:
        return {
            "type": "infrastructure_setup",
            "docker": {
                "dockerfile_created": True,
                "docker_compose_created": True,
            },
            "cicd": {
                "pipeline_created": True,
                "self_hosted_runner": True,
            },
            "deployment": {
                "platform": "coolify",
                "rollback_enabled": True,
                "healthcheck_enabled": True,
            },
        }

    def validate_command(self, command: str) -> tuple[bool, Optional[str]]:
        for forbidden in self.FORBIDDEN_COMMANDS:
            if forbidden in command:
                return False, f"Forbidden command detected: {forbidden}"
        return True, None

    def validate_env_vars(self, content: str) -> tuple[bool, list[str]]:
        hardcoded_patterns = [
            "password=",
            "secret=",
            "api_key=",
            "token=",
        ]
        issues = []
        for pattern in hardcoded_patterns:
            if pattern.lower() in content.lower():
                issues.append(f"Potential hardcoded secret: {pattern}")
        return len(issues) == 0, issues
