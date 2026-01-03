from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ProjectAgentRole(str, Enum):
    """Role of an agent in a project."""

    PRIMARY = "primary"  # Main agent responsible for the area
    SECONDARY = "secondary"  # Supporting agent
    REVIEWER = "reviewer"  # Reviews work from other agents


class ProjectAgentBase(SQLModel):
    """Base model for project-agent association."""

    project_id: int = Field(foreign_key="project.id", index=True)
    agent_id: int = Field(foreign_key="agent.id", index=True)
    role: ProjectAgentRole = Field(default=ProjectAgentRole.PRIMARY)
    scope: Optional[str] = Field(default=None)  # JSON string defining scope
    is_active: bool = Field(default=True)


class ProjectAgent(ProjectAgentBase, table=True):
    """Association between projects and agents."""

    id: Optional[int] = Field(default=None, primary_key=True)
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    last_activity_at: Optional[datetime] = None


class ProjectAgentCreate(ProjectAgentBase):
    """Schema for creating project-agent association."""

    pass


class ProjectAgentRead(ProjectAgentBase):
    """Schema for reading project-agent association."""

    id: int
    assigned_at: datetime
    last_activity_at: Optional[datetime]


class ProjectAgentUpdate(SQLModel):
    """Schema for updating project-agent association."""

    role: Optional[ProjectAgentRole] = None
    scope: Optional[str] = None
    is_active: Optional[bool] = None
