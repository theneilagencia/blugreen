from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ProjectStatus(str, Enum):
    """Project lifecycle states.
    
    Lifecycle flow:
    DRAFT → ACTIVE (via workflows/agents) → TERMINATING → TERMINATED → DELETED
    
    Rules:
    - ACTIVE projects cannot be deleted directly
    - Projects must be TERMINATED before deletion
    - TERMINATING is a transitional state during shutdown
    """
    DRAFT = "draft"
    PLANNING = "planning"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DEPLOYING = "deploying"
    DEPLOYED = "deployed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"
    # Phase 3 statuses
    ASSUMING = "assuming"
    DIAGNOSING = "diagnosing"
    EVOLVING = "evolving"
    # Lifecycle states
    ACTIVE = "active"
    TERMINATING = "terminating"
    TERMINATED = "terminated"


class ProjectBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    repository_url: Optional[str] = None
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)



class Project(ProjectBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class ProjectCreate(ProjectBase):
    pass


class ProjectRead(ProjectBase):
    id: int
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(SQLModel):
    name: Optional[str] = None
    description: Optional[str] = None
    repository_url: Optional[str] = None
    status: Optional[ProjectStatus] = None
