from datetime import datetime
from enum import Enum
from typing import Optional

from sqlmodel import Field, SQLModel


class WorkflowStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class WorkflowStepType(str, Enum):
    INTERPRET_REQUIREMENT = "interpret_requirement"
    CREATE_PLAN = "create_plan"
    VALIDATE_PLAN = "validate_plan"
    GENERATE_CODE = "generate_code"
    CREATE_TESTS = "create_tests"
    RUN_TESTS = "run_tests"
    BUILD = "build"
    DEPLOY = "deploy"
    MONITOR = "monitor"
    ROLLBACK = "rollback"
    UX_REVIEW = "ux_review"
    UI_REFINEMENT = "ui_refinement"


class WorkflowBase(SQLModel):
    name: str = Field(index=True)
    project_id: int = Field(foreign_key="project.id")
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    current_step: Optional[str] = None


class Workflow(WorkflowBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None


class WorkflowRead(WorkflowBase):
    id: int
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime]


class WorkflowStepBase(SQLModel):
    workflow_id: int = Field(foreign_key="workflow.id")
    step_type: WorkflowStepType
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING)
    order: int
    input_data: Optional[str] = None
    output_data: Optional[str] = None
    error_message: Optional[str] = None


class WorkflowStep(WorkflowStepBase, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class WorkflowStepRead(WorkflowStepBase):
    id: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
