from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.models.project import Project, ProjectStatus
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType


class MainWorkflow:
    STEPS = [
        WorkflowStepType.INTERPRET_REQUIREMENT,
        WorkflowStepType.CREATE_PLAN,
        WorkflowStepType.VALIDATE_PLAN,
        WorkflowStepType.GENERATE_CODE,
        WorkflowStepType.CREATE_TESTS,
        WorkflowStepType.RUN_TESTS,
        WorkflowStepType.BUILD,
        WorkflowStepType.DEPLOY,
        WorkflowStepType.MONITOR,
    ]

    def __init__(self, session: Session, project: Project):
        self.session = session
        self.project = project
        self.workflow: Optional[Workflow] = None
        self.current_step_index = 0

    def initialize(self) -> Workflow:
        self.workflow = Workflow(
            name=f"Main Workflow - {self.project.name}",
            project_id=self.project.id,
            status=WorkflowStatus.PENDING,
        )
        self.session.add(self.workflow)
        self.session.commit()
        self.session.refresh(self.workflow)

        for order, step_type in enumerate(self.STEPS):
            step = WorkflowStep(
                workflow_id=self.workflow.id,
                step_type=step_type,
                status=WorkflowStatus.PENDING,
                order=order,
            )
            self.session.add(step)

        self.session.commit()
        return self.workflow

    def start(self) -> dict[str, Any]:
        if not self.workflow:
            self.initialize()

        self.workflow.status = WorkflowStatus.IN_PROGRESS
        self.session.add(self.workflow)

        self.project.status = ProjectStatus.IN_PROGRESS
        self.session.add(self.project)

        self.session.commit()

        return {
            "status": "started",
            "workflow_id": self.workflow.id,
            "total_steps": len(self.STEPS),
        }

    def get_current_step(self) -> Optional[WorkflowStep]:
        if not self.workflow:
            return None

        steps = (
            self.session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == self.workflow.id)
            .order_by(WorkflowStep.order)
            .all()
        )

        for step in steps:
            if step.status in [WorkflowStatus.PENDING, WorkflowStatus.IN_PROGRESS]:
                return step

        return None

    def advance_step(
        self, success: bool = True, error_message: Optional[str] = None
    ) -> dict[str, Any]:
        current_step = self.get_current_step()
        if not current_step:
            return {"status": "completed", "message": "All steps completed"}

        if success:
            current_step.status = WorkflowStatus.COMPLETED
            current_step.completed_at = datetime.utcnow()
        else:
            current_step.status = WorkflowStatus.FAILED
            current_step.error_message = error_message
            return self._handle_failure(current_step)

        self.session.add(current_step)
        self.session.commit()

        next_step = self.get_current_step()
        if not next_step:
            self._complete_workflow()
            return {"status": "completed", "message": "Workflow completed successfully"}

        return {
            "status": "advanced",
            "current_step": next_step.step_type.value,
            "step_order": next_step.order,
        }

    def _handle_failure(self, failed_step: WorkflowStep) -> dict[str, Any]:
        self.session.add(failed_step)
        self.session.commit()

        if failed_step.order > 0:
            return {
                "status": "failed",
                "message": f"Step {failed_step.step_type.value} failed",
                "action": "return_to_previous_step",
                "error": failed_step.error_message,
            }

        self.workflow.status = WorkflowStatus.FAILED
        self.session.add(self.workflow)
        self.session.commit()

        return {
            "status": "failed",
            "message": "Workflow failed at first step",
            "error": failed_step.error_message,
        }

    def _complete_workflow(self) -> None:
        self.workflow.status = WorkflowStatus.COMPLETED
        self.workflow.completed_at = datetime.utcnow()
        self.session.add(self.workflow)

        self.project.status = ProjectStatus.DEPLOYED
        self.session.add(self.project)

        self.session.commit()

    def rollback(self) -> dict[str, Any]:
        if not self.workflow:
            return {"status": "error", "message": "No workflow to rollback"}

        self.workflow.status = WorkflowStatus.ROLLED_BACK
        self.session.add(self.workflow)

        self.project.status = ProjectStatus.ROLLED_BACK
        self.session.add(self.project)

        self.session.commit()

        return {
            "status": "rolled_back",
            "message": f"Workflow {self.workflow.id} rolled back",
        }

    def get_status(self) -> dict[str, Any]:
        if not self.workflow:
            return {"status": "not_initialized"}

        steps = (
            self.session.query(WorkflowStep)
            .filter(WorkflowStep.workflow_id == self.workflow.id)
            .order_by(WorkflowStep.order)
            .all()
        )

        return {
            "workflow_id": self.workflow.id,
            "workflow_status": self.workflow.status.value,
            "steps": [
                {
                    "order": s.order,
                    "type": s.step_type.value,
                    "status": s.status.value,
                    "started_at": s.started_at.isoformat() if s.started_at else None,
                    "completed_at": s.completed_at.isoformat() if s.completed_at else None,
                    "error": s.error_message,
                }
                for s in steps
            ],
        }
