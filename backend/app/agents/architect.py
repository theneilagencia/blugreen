import json
import logging
from typing import Any, Optional

from app.agents.base import BaseAgent
from app.models.agent import AgentType
from app.models.task import Task, TaskType

logger = logging.getLogger(__name__)

ARCHITECT_SYSTEM_PROMPT = """You are an expert software architect. Your role is to:
- Define clear system architecture with well-defined layers
- Create boundaries between components
- Design module structures
- Define contracts between layers

You must follow these constraints:
- Use only: Python 3.11, FastAPI, SQLModel for backend
- Use only: Next.js, Tailwind CSS for frontend
- Use only: Docker, Coolify for infrastructure
- Use only: Ollama with open-source models for LLM

Never write implementation code. Only define structure and contracts.
Always respond with valid JSON."""


class ArchitectAgent(BaseAgent):
    agent_type = AgentType.ARCHITECT
    system_prompt = ARCHITECT_SYSTEM_PROMPT
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
            logger.error(f"Architect agent error: {e}")
            self.complete_task(task, success=False, error_message=str(e))
            return {
                "status": "error",
                "error": str(e),
            }

    async def _design_architecture(self, task: Task) -> dict[str, Any]:
        prompt = f"""Design a software architecture for the following requirement:

{task.description}

Provide a JSON response with this structure:
{{
    "layers": [
        {{"name": "layer_name", "description": "what it does", "technology": "tech stack"}}
    ],
    "boundaries": ["boundary rule 1", "boundary rule 2"],
    "contracts": [
        {{"from": "layer1", "to": "layer2", "type": "communication type"}}
    ],
    "modules": [
        {{"name": "module_name", "layer": "which layer", "responsibility": "what it does"}}
    ]
}}

Remember:
- Backend: Python 3.11, FastAPI, SQLModel
- Frontend: Next.js, Tailwind CSS
- Infrastructure: Docker, Coolify
- LLM: Ollama with open-source models"""

        try:
            response = await self.ask_llm(prompt, temperature=0.3)
            return self._parse_architecture_response(response)
        except Exception as e:
            logger.warning(f"LLM unavailable, using fallback architecture: {e}")
            return self._get_fallback_architecture()

    def _parse_architecture_response(self, response: str) -> dict[str, Any]:
        try:
            start_idx = response.find("{")
            end_idx = response.rfind("}") + 1
            if start_idx != -1 and end_idx > start_idx:
                json_str = response[start_idx:end_idx]
                return json.loads(json_str)
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return self._get_fallback_architecture()

    def _get_fallback_architecture(self) -> dict[str, Any]:
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
            "modules": [
                {
                    "name": "project_manager",
                    "layer": "orchestrator",
                    "responsibility": "Manage project lifecycle",
                },
                {
                    "name": "task_planner",
                    "layer": "orchestrator",
                    "responsibility": "Break down tasks and assign to agents",
                },
                {
                    "name": "state_manager",
                    "layer": "orchestrator",
                    "responsibility": "Track workflow state",
                },
            ],
        }
