from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class TaskType(str, Enum):
    PLANNING = "planning"
    BACKEND = "backend"
    FRONTEND = "frontend"
    TESTING = "testing"
    DEPLOYMENT = "deployment"
    UX_REVIEW = "ux_review"
    UI_REFINEMENT = "ui_refinement"
    INFRA = "infra"


class TaskBase(SQLModel):
    title: str = Field(index=True)
    description: Optional[str] = None
    task_type: TaskType
    status: TaskStatus = Field(default=TaskStatus.PENDING)
    project_id: int = Field(foreign_key="project.id")
    assigned_agent: Optional[str] = None
    error_message: Optional[str] = None


class Task(TaskBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def __init__(self, **data):
        """Initialize Task with defensive title validation."""
        # Get title and task_type from data
        title = data.get("title")
        task_type = data.get("task_type")
        
        # Validate and fix title if needed
        if title is None or (isinstance(title, str) and not title.strip()):
            # Generate fallback title based on task_type
            if isinstance(task_type, TaskType):
                task_type_str = task_type.value.replace("_", " ").title()
            elif isinstance(task_type, str):
                task_type_str = task_type.replace("_", " ").title()
            else:
                task_type_str = "Task"
            
            data["title"] = f"Untitled {task_type_str}"
        elif isinstance(title, str):
            # Strip whitespace from valid titles
            data["title"] = title.strip()
        
        # Call parent __init__
        super().__init__(**data)


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class TaskUpdate(SQLModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[TaskStatus] = None
    assigned_agent: Optional[str] = None
    error_message: Optional[str] = None
