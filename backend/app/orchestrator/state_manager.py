from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep


class StateManager:
    def __init__(self, session: Session):
        self.session = session

    def get_project_state(self, project_id: int) -> dict[str, Any]:
        project = self.session.get(Project, project_id)
        if not project:
            return {"error": "Project not found"}

        tasks = self.session.exec(
            select(Task).where(Task.project_id == project_id)
        ).all()

        workflows = self.session.exec(
            select(Workflow).where(Workflow.project_id == project_id)
        ).all()

        return {
            "project": {
                "id": project.id,
                "name": project.name,
                "status": project.status,
                "created_at": project.created_at.isoformat(),
                "updated_at": project.updated_at.isoformat(),
            },
            "tasks": {
                "total": len(tasks),
                "pending": sum(1 for t in tasks if t.status == TaskStatus.PENDING),
                "in_progress": sum(1 for t in tasks if t.status == TaskStatus.IN_PROGRESS),
                "completed": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
                "failed": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
            },
            "workflows": {
                "total": len(workflows),
                "active": sum(1 for w in workflows if w.status == WorkflowStatus.IN_PROGRESS),
                "completed": sum(1 for w in workflows if w.status == WorkflowStatus.COMPLETED),
            },
        }

    def update_project_status(self, project_id: int, status: ProjectStatus) -> Optional[Project]:
        project = self.session.get(Project, project_id)
        if not project:
            return None

        project.status = status
        project.updated_at = datetime.utcnow()
        self.session.add(project)
        self.session.commit()
        self.session.refresh(project)
        return project

    def get_pending_tasks(self, project_id: int) -> list[Task]:
        return list(self.session.exec(
            select(Task).where(
                Task.project_id == project_id,
                Task.status == TaskStatus.PENDING
            )
        ).all())

    def get_active_workflow(self, project_id: int) -> Optional[Workflow]:
        return self.session.exec(
            select(Workflow).where(
                Workflow.project_id == project_id,
                Workflow.status == WorkflowStatus.IN_PROGRESS
            )
        ).first()

    def get_workflow_steps(self, workflow_id: int) -> list[WorkflowStep]:
        return list(self.session.exec(
            select(WorkflowStep).where(WorkflowStep.workflow_id == workflow_id).order_by(WorkflowStep.order)
        ).all())

    def can_proceed_to_next_step(self, workflow_id: int) -> tuple[bool, Optional[str]]:
        steps = self.get_workflow_steps(workflow_id)
        if not steps:
            return False, "No workflow steps found"

        current_step = None
        for step in steps:
            if step.status == WorkflowStatus.IN_PROGRESS:
                current_step = step
                break
            if step.status == WorkflowStatus.FAILED:
                return False, f"Step {step.step_type} failed: {step.error_message}"

        if current_step is None:
            pending_steps = [s for s in steps if s.status == WorkflowStatus.PENDING]
            if pending_steps:
                return True, None
            return False, "All steps completed"

        return False, f"Step {current_step.step_type} still in progress"
