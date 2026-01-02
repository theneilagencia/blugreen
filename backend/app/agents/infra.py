import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType

logger = logging.getLogger(__name__)

INFRA_SYSTEM_PROMPT = """You are an expert infrastructure engineer. Your role is to:
- Create Docker configurations
- Set up CI/CD pipelines
- Configure deployments
- Manage environments
- Set up monitoring

You must follow these constraints:
- Use only: Docker, Coolify, self-hosted CI
- Never use paid services
- Never expose secrets
- Never execute destructive commands
- Never hardcode environment variables

Always respond with valid JSON."""


class InfraAgent(BaseAgent):
    agent_type = AgentType.INFRA
    system_prompt = INFRA_SYSTEM_PROMPT
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
            logger.error(f"Infra agent error: {e}")
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _setup_infrastructure(self, task: Task) -> dict[str, Any]:
        prompt = f"""Create infrastructure configuration for the following requirement:

{task.description}

Provide a JSON response with this structure:
{{
    "type": "infrastructure_setup",
    "docker": {{
        "dockerfile": "FROM python:3.11-slim\\n...",
        "docker_compose": "version: '3.8'\\nservices:\\n..."
    }},
    "cicd": {{
        "pipeline": "name: CI\\non: [push]\\njobs:\\n...",
        "stages": ["lint", "test", "build", "deploy"]
    }},
    "deployment": {{
        "platform": "coolify",
        "config": {{...}},
        "rollback_strategy": "automatic",
        "healthcheck": "/health"
    }},
    "environment_variables": [
        {{"name": "VAR_NAME", "description": "what it's for", "required": true}}
    ]
}}

Use Docker, Coolify, and self-hosted CI. Never include actual secrets."""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_infra_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback infrastructure: {e}")
            return self._get_fallback_infrastructure()

    def _parse_infra_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                docker_content = json.dumps(result.get("docker", {}))
                is_valid, issues = self.validate_env_vars(docker_content)
                if not is_valid:
                    logger.warning(f"Security issues detected: {issues}")
                    result["security_warnings"] = issues
                return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_infrastructure()

    def _get_fallback_infrastructure(self) -> dict[str, Any]:
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
            "note": "LLM unavailable - manual configuration required",
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
