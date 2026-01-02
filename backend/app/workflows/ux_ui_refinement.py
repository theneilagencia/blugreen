from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session

from app.models.project import Project
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType


class UXUIRefinementWorkflow:
    STEPS = [
        WorkflowStepType.GENERATE_CODE,
        WorkflowStepType.UX_REVIEW,
        WorkflowStepType.UI_REFINEMENT,
        WorkflowStepType.RUN_TESTS,
    ]

    MAX_ITERATIONS = 3

    def __init__(self, session: Session, project: Project):
        self.session = session
        self.project = project
        self.workflow: Optional[Workflow] = None
        self.iteration = 0

    def initialize(self) -> Workflow:
        self.workflow = Workflow(
            name=f"UX/UI Refinement - {self.project.name}",
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
        self.session.commit()

        return {
            "status": "started",
            "workflow_id": self.workflow.id,
            "workflow_type": "ux_ui_refinement",
            "max_iterations": self.MAX_ITERATIONS,
        }

    def execute_ux_review(self, ux_results: dict[str, Any]) -> dict[str, Any]:
        if not ux_results.get("ux_approved", False):
            return {
                "status": "needs_adjustment",
                "action": "adjust_flow",
                "issues": ux_results.get("rule_results", []),
                "recommendations": ux_results.get("recommendations", []),
            }

        return {
            "status": "approved",
            "message": "UX review passed",
        }

    def execute_ui_refinement(self, ui_results: dict[str, Any]) -> dict[str, Any]:
        if not ui_results.get("ui_approved", False):
            self.iteration += 1

            if self.iteration >= self.MAX_ITERATIONS:
                return {
                    "status": "max_iterations_reached",
                    "message": f"UI refinement reached max iterations ({self.MAX_ITERATIONS})",
                    "final_score": ui_results.get("total_score", 0),
                }

            return {
                "status": "needs_refinement",
                "action": "refine_visual",
                "iteration": self.iteration,
                "score": ui_results.get("total_score", 0),
                "quality_scores": ui_results.get("quality_scores", []),
            }

        return {
            "status": "approved",
            "message": "UI refinement passed",
            "final_score": ui_results.get("total_score", 0),
        }

    def revalidate(self) -> dict[str, Any]:
        return {
            "status": "revalidating",
            "iteration": self.iteration,
            "action": "run_ux_review_again",
        }

    def approve(self) -> dict[str, Any]:
        if not self.workflow:
            return {"status": "error", "message": "No workflow to approve"}

        self.workflow.status = WorkflowStatus.COMPLETED
        self.workflow.completed_at = datetime.utcnow()
        self.session.add(self.workflow)
        self.session.commit()

        return {
            "status": "approved",
            "message": "UX/UI refinement workflow completed",
            "total_iterations": self.iteration,
        }

    def get_status(self) -> dict[str, Any]:
        if not self.workflow:
            return {"status": "not_initialized"}

        steps = self.session.query(WorkflowStep).filter(
            WorkflowStep.workflow_id == self.workflow.id
        ).order_by(WorkflowStep.order).all()

        return {
            "workflow_id": self.workflow.id,
            "workflow_type": "ux_ui_refinement",
            "workflow_status": self.workflow.status.value,
            "current_iteration": self.iteration,
            "max_iterations": self.MAX_ITERATIONS,
            "steps": [
                {
                    "order": s.order,
                    "type": s.step_type.value,
                    "status": s.status.value,
                }
                for s in steps
            ],
        }
