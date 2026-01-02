from typing import Any

from sqlmodel import Session

from app.models.project import Project
from app.models.task import Task, TaskType
from app.models.workflow import (
    Workflow,
    WorkflowStatus,
    WorkflowStep,
    WorkflowStepType,
)


class Planner:
    STANDARD_WORKFLOW_STEPS = [
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

    UX_UI_REFINEMENT_STEPS = [
        WorkflowStepType.GENERATE_CODE,
        WorkflowStepType.UX_REVIEW,
        WorkflowStepType.UI_REFINEMENT,
        WorkflowStepType.RUN_TESTS,
    ]

    def __init__(self, session: Session):
        self.session = session

    def create_project_plan(self, project: Project, requirements: str) -> dict[str, Any]:
        workflow = Workflow(
            name=f"Main workflow for {project.name}",
            project_id=project.id,
            status=WorkflowStatus.PENDING,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = []
        for order, step_type in enumerate(self.STANDARD_WORKFLOW_STEPS):
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_type=step_type,
                status=WorkflowStatus.PENDING,
                order=order,
            )
            self.session.add(step)
            steps.append(step)

        self.session.commit()

        tasks = self._create_tasks_from_requirements(project, requirements)

        return {
            "workflow_id": workflow.id,
            "steps": [{"order": s.order, "type": s.step_type.value} for s in steps],
            "tasks": [{"id": t.id, "title": t.title, "type": t.task_type.value} for t in tasks],
        }

    def _create_tasks_from_requirements(self, project: Project, requirements: str) -> list[Task]:
        tasks = []

        planning_task = Task(
            title="Architecture Planning",
            description="Define system architecture and boundaries",
            task_type=TaskType.PLANNING,
            project_id=project.id,
        )
        self.session.add(planning_task)
        tasks.append(planning_task)

        backend_task = Task(
            title="Backend Implementation",
            description="Implement API endpoints and database models",
            task_type=TaskType.BACKEND,
            project_id=project.id,
        )
        self.session.add(backend_task)
        tasks.append(backend_task)

        frontend_task = Task(
            title="Frontend Implementation",
            description="Implement user interface following design system",
            task_type=TaskType.FRONTEND,
            project_id=project.id,
        )
        self.session.add(frontend_task)
        tasks.append(frontend_task)

        ux_task = Task(
            title="UX Review",
            description="Evaluate UX against rules engine",
            task_type=TaskType.UX_REVIEW,
            project_id=project.id,
        )
        self.session.add(ux_task)
        tasks.append(ux_task)

        ui_task = Task(
            title="UI Refinement",
            description="Refine UI according to quality criteria",
            task_type=TaskType.UI_REFINEMENT,
            project_id=project.id,
        )
        self.session.add(ui_task)
        tasks.append(ui_task)

        testing_task = Task(
            title="Quality Assurance",
            description="Run all tests and quality checks",
            task_type=TaskType.TESTING,
            project_id=project.id,
        )
        self.session.add(testing_task)
        tasks.append(testing_task)

        deploy_task = Task(
            title="Deployment",
            description="Deploy to production with rollback capability",
            task_type=TaskType.DEPLOYMENT,
            project_id=project.id,
        )
        self.session.add(deploy_task)
        tasks.append(deploy_task)

        self.session.commit()
        return tasks

    def create_ux_ui_refinement_plan(self, project: Project) -> dict[str, Any]:
        workflow = Workflow(
            name=f"UX/UI Refinement for {project.name}",
            project_id=project.id,
            status=WorkflowStatus.PENDING,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = []
        for order, step_type in enumerate(self.UX_UI_REFINEMENT_STEPS):
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_type=step_type,
                status=WorkflowStatus.PENDING,
                order=order,
            )
            self.session.add(step)
            steps.append(step)

        self.session.commit()

        return {
            "workflow_id": workflow.id,
            "steps": [{"order": s.order, "type": s.step_type.value} for s in steps],
        }

    def validate_plan(self, workflow_id: int) -> tuple[bool, list[str]]:
        workflow = self.session.get(Workflow, workflow_id)
        if not workflow:
            return False, ["Workflow not found"]

        issues = []

        steps = self.session.exec(
            WorkflowStep.__table__.select().where(WorkflowStep.workflow_id == workflow_id)
        ).all()

        if not steps:
            issues.append("No workflow steps defined")

        has_tests = any(s.step_type == WorkflowStepType.RUN_TESTS for s in steps)
        has_deploy = any(s.step_type == WorkflowStepType.DEPLOY for s in steps)

        if has_deploy and not has_tests:
            issues.append("Cannot deploy without running tests (CONSTRAINTS violation)")

        return len(issues) == 0, issues
