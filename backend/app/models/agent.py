from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class AgentType(str, Enum):
    ARCHITECT = "architect"
    BACKEND = "backend"
    FRONTEND = "frontend"
    INFRA = "infra"
    QA = "qa"
    UX = "ux"
    UI_REFINEMENT = "ui_refinement"


class AgentStatus(str, Enum):
    IDLE = "idle"
    WORKING = "working"
    BLOCKED = "blocked"
    ERROR = "error"


class AgentBase(SQLModel):
    name: str = Field(index=True)
    agent_type: AgentType
    status: AgentStatus = Field(default=AgentStatus.IDLE)
    current_task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    capabilities: str = Field(default="")
    restrictions: str = Field(default="")


class Agent(AgentBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active_at: Optional[datetime] = None


class AgentRead(AgentBase):
    id: int
    created_at: datetime
    last_active_at: Optional[datetime]
