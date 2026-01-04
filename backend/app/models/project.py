from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class ProjectStatus(str, Enum):
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


class ProjectBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None
    repository_url: Optional[str] = None
    status: ProjectStatus = Field(default=ProjectStatus.DRAFT)
    
    # Assume Flow fields
    assumption_status: Optional[str] = None  # "pending", "in_progress", "completed", "failed"
    assumption_error: Optional[str] = None
    detected_branch: Optional[str] = None
    assumption_started_at: Optional[datetime] = None
    assumption_completed_at: Optional[datetime] = None


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
