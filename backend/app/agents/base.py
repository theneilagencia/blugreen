import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.models.agent import Agent, AgentStatus, AgentType
from app.models.task import Task, TaskStatus
from app.services.ollama import OllamaClient, OllamaError, get_ollama_client

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    agent_type: AgentType
    capabilities: list[str] = []
    restrictions: list[str] = []
    system_prompt: str = "You are a helpful AI assistant."

    def __init__(self, session: Session, ollama_client: Optional[OllamaClient] = None):
        self.session = session
        self._agent_record: Optional[Agent] = None
        self._ollama = ollama_client or get_ollama_client()

    @property
    def name(self) -> str:
        return f"{self.agent_type.value}_agent"

    def get_or_create_agent_record(self) -> Agent:
        if self._agent_record:
            return self._agent_record

        agent = self.session.query(Agent).filter(Agent.agent_type == self.agent_type).first()

        if not agent:
            agent = Agent(
                name=self.name,
                agent_type=self.agent_type,
                capabilities=",".join(self.capabilities),
                restrictions=",".join(self.restrictions),
            )
            self.session.add(agent)
            self.session.commit()
            self.session.refresh(agent)

        self._agent_record = agent
        return agent

    def update_status(self, status: AgentStatus) -> None:
        agent = self.get_or_create_agent_record()
        agent.status = status
        agent.last_active_at = datetime.utcnow()
        self.session.add(agent)
        self.session.commit()

    def assign_task(self, task: Task) -> None:
        agent = self.get_or_create_agent_record()
        agent.current_task_id = task.id
        agent.status = AgentStatus.WORKING
        agent.last_active_at = datetime.utcnow()
        self.session.add(agent)

        task.assigned_agent = self.name
        task.status = TaskStatus.IN_PROGRESS
        self.session.add(task)
        self.session.commit()

    def complete_task(
        self, task: Task, success: bool = True, error_message: Optional[str] = None
    ) -> None:
        agent = self.get_or_create_agent_record()
        agent.current_task_id = None
        agent.status = AgentStatus.IDLE
        agent.last_active_at = datetime.utcnow()
        self.session.add(agent)

        task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
        task.completed_at = datetime.utcnow()
        if error_message:
            task.error_message = error_message
        self.session.add(task)
        self.session.commit()

    @abstractmethod
    async def execute(self, task: Task) -> dict[str, Any]:
        pass

    @abstractmethod
    def validate_task(self, task: Task) -> tuple[bool, Optional[str]]:
        pass

    def can_handle_task(self, task: Task) -> bool:
        return True

    async def ask_llm(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        try:
            response = await self._ollama.generate(
                prompt=prompt,
                system=self.system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response
        except OllamaError as e:
            logger.error(f"LLM error in {self.name}: {e}")
            raise

    async def chat_with_llm(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> str:
        full_messages = [{"role": "system", "content": self.system_prompt}] + messages
        try:
            response = await self._ollama.chat(
                messages=full_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return response
        except OllamaError as e:
            logger.error(f"LLM chat error in {self.name}: {e}")
            raise

    async def is_llm_available(self) -> bool:
        return await self._ollama.is_available()
