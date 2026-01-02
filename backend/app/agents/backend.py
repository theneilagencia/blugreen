import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType

logger = logging.getLogger(__name__)

BACKEND_SYSTEM_PROMPT = """You are an expert backend developer. Your role is to:
- Create REST API endpoints using FastAPI
- Design database models using SQLModel
- Write business logic
- Implement validation and error handling
- Write comprehensive tests

You must follow these constraints:
- Use only: Python 3.11, FastAPI, SQLModel
- Follow RESTful API design principles
- Always include proper error handling
- Always write tests for new code

Never modify frontend code or infrastructure.
Always respond with valid JSON."""


class BackendAgent(BaseAgent):
    agent_type = AgentType.BACKEND
    system_prompt = BACKEND_SYSTEM_PROMPT
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
            logger.error(f"Backend agent error: {e}")
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _implement_backend(self, task: Task) -> dict[str, Any]:
        prompt = f"""Implement backend code for the following requirement:

{task.description}

Provide a JSON response with this structure:
{{
    "type": "backend_implementation",
    "models": [
        {{
            "name": "ModelName",
            "fields": [{{"name": "field_name", "type": "field_type", "required": true}}],
            "code": "class ModelName(SQLModel, table=True): ..."
        }}
    ],
    "endpoints": [
        {{
            "method": "GET|POST|PUT|DELETE",
            "path": "/api/path",
            "description": "what it does",
            "code": "@router.get('/path')\\nasync def handler(): ..."
        }}
    ],
    "business_logic": [
        {{
            "name": "function_name",
            "description": "what it does",
            "code": "def function_name(): ..."
        }}
    ]
}}

Use FastAPI and SQLModel. Include proper type hints and error handling."""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_backend_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback implementation: {e}")
            return self._get_fallback_backend()

    async def _write_tests(self, task: Task) -> dict[str, Any]:
        prompt = f"""Write tests for the following requirement:

{task.description}

Provide a JSON response with this structure:
{{
    "type": "test_implementation",
    "unit_tests": [
        {{
            "name": "test_function_name",
            "description": "what it tests",
            "code": "def test_function_name(): ..."
        }}
    ],
    "integration_tests": [
        {{
            "name": "test_integration_name",
            "description": "what it tests",
            "code": "async def test_integration_name(client): ..."
        }}
    ],
    "fixtures": [
        {{
            "name": "fixture_name",
            "code": "@pytest.fixture\\ndef fixture_name(): ..."
        }}
    ]
}}

Use pytest and pytest-asyncio. Include proper assertions and edge cases."""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_test_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback tests: {e}")
            return self._get_fallback_tests()

    def _parse_backend_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_backend()

    def _parse_test_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_tests()

    def _get_fallback_backend(self) -> dict[str, Any]:
        return {
            "type": "backend_implementation",
            "models": [],
            "endpoints": [],
            "business_logic": [],
            "note": "LLM unavailable - manual implementation required",
        }

    def _get_fallback_tests(self) -> dict[str, Any]:
        return {
            "type": "test_implementation",
            "unit_tests": [],
            "integration_tests": [],
            "fixtures": [],
            "note": "LLM unavailable - manual test writing required",
        }
