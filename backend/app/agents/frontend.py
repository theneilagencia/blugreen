import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType

logger = logging.getLogger(__name__)

FRONTEND_SYSTEM_PROMPT = """You are an expert frontend developer. Your role is to:
- Create functional UI using Next.js and Tailwind CSS
- Implement components following the Design System
- Connect frontend to backend APIs
- Handle state management
- Implement routing

You must follow these constraints:
- Use only: Next.js, Tailwind CSS, TypeScript
- Only use allowed components: Button, Input, Select, Modal, Table, Card, Alert, Badge
- Follow the Design System tokens for spacing and border radius
- Never modify backend code

Always respond with valid JSON."""


class FrontendAgent(BaseAgent):
    agent_type = AgentType.FRONTEND
    system_prompt = FRONTEND_SYSTEM_PROMPT
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
            logger.error(f"Frontend agent error: {e}")
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _implement_frontend(self, task: Task) -> dict[str, Any]:
        prompt = f"""Implement frontend code for the following requirement:

{task.description}

Provide a JSON response with this structure:
{{
    "type": "frontend_implementation",
    "pages": [
        {{
            "name": "PageName",
            "path": "/route/path",
            "description": "what it does",
            "code": "export default function PageName() {{ ... }}"
        }}
    ],
    "components": [
        {{
            "name": "ComponentName",
            "description": "what it does",
            "code": "export function ComponentName() {{ ... }}"
        }}
    ],
    "api_connections": [
        {{
            "endpoint": "/api/endpoint",
            "method": "GET|POST|PUT|DELETE",
            "description": "what it fetches"
        }}
    ],
    "components_used": ["Button", "Input", "Card"]
}}

Only use these allowed components: {', '.join(self.ALLOWED_COMPONENTS)}
Use Next.js, TypeScript, and Tailwind CSS."""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_frontend_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback implementation: {e}")
            return self._get_fallback_frontend()

    def _parse_frontend_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                result = json.loads(json_str)
                components_used = result.get("components_used", [])
                is_valid, invalid = self.validate_component_usage(components_used)
                if not is_valid:
                    logger.warning(f"Invalid components detected: {invalid}")
                    result["design_system_violations"] = invalid
                result["design_system_compliance"] = is_valid
                return result
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_frontend()

    def _get_fallback_frontend(self) -> dict[str, Any]:
        return {
            "type": "frontend_implementation",
            "pages": [],
            "components": [],
            "api_connections": [],
            "components_used": [],
            "design_system_compliance": True,
            "note": "LLM unavailable - manual implementation required",
        }

    def validate_component_usage(self, components: list[str]) -> tuple[bool, list[str]]:
        invalid_components = [c for c in components if c not in self.ALLOWED_COMPONENTS]
        return len(invalid_components) == 0, invalid_components
