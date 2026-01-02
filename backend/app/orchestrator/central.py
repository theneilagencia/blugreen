from datetime import datetime
from typing import Any, Optional

from sqlmodel import Session, select

from app.agents import (
    ArchitectAgent,
    BackendAgent,
    FrontendAgent,
    InfraAgent,
    QAAgent,
    UIRefinementAgent,
    UXAgent,
)
from app.models.agent import AgentType
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType
from app.orchestrator.planner import Planner
from app.orchestrator.state_manager import StateManager


class CentralOrchestrator:
    def __init__(self, session: Session):
        self.session = session
        self.state_manager = StateManager(session)
        self.planner = Planner(session)
        self._agents = self._initialize_agents()

    def _initialize_agents(self) -> dict[AgentType, Any]:
        return {
            AgentType.ARCHITECT: ArchitectAgent(self.session),
            AgentType.BACKEND: BackendAgent(self.session),
            AgentType.FRONTEND: FrontendAgent(self.session),
            AgentType.INFRA: InfraAgent(self.session),
            AgentType.QA: QAAgent(self.session),
            AgentType.UX: UXAgent(self.session),
            AgentType.UI_REFINEMENT: UIRefinementAgent(self.session),
        }

    def get_agent_for_task(self, task: Task) -> Optional[Any]:
        task_to_agent = {
            TaskType.PLANNING: AgentType.ARCHITECT,
            TaskType.BACKEND: AgentType.BACKEND,
            TaskType.FRONTEND: AgentType.FRONTEND,
            TaskType.TESTING: AgentType.QA,
            TaskType.DEPLOYMENT: AgentType.INFRA,
            TaskType.UX_REVIEW: AgentType.UX,
            TaskType.UI_REFINEMENT: AgentType.UI_REFINEMENT,
        }
        agent_type = task_to_agent.get(task.task_type)
        if agent_type:
            return self._agents.get(agent_type)
        return None

    async def start_project(self, project: Project, requirements: str) -> dict[str, Any]:
        self.state_manager.update_project_status(project.id, ProjectStatus.PLANNING)

        plan = self.planner.create_project_plan(project, requirements)

        is_valid, issues = self.planner.validate_plan(plan["workflow_id"])
        if not is_valid:
            return {
                "status": "error",
                "message": "Plan validation failed",
                "issues": issues,
            }

        self.state_manager.update_project_status(project.id, ProjectStatus.IN_PROGRESS)

        return {
            "status": "success",
            "project_id": project.id,
            "plan": plan,
        }

    async def execute_next_step(self, project_id: int) -> dict[str, Any]:
        workflow = self.state_manager.get_active_workflow(project_id)
        if not workflow:
            workflows = self.session.exec(
                select(Workflow).where(
                    Workflow.project_id == project_id, Workflow.status == WorkflowStatus.PENDING
                )
            ).first()
            if workflows:
                workflow = workflows
                workflow.status = WorkflowStatus.IN_PROGRESS
                self.session.add(workflow)
                self.session.commit()
            else:
                return {"status": "error", "message": "No workflow found"}

        can_proceed, message = self.state_manager.can_proceed_to_next_step(workflow.id)
        if not can_proceed and message != "All steps completed":
            return {"status": "blocked", "message": message}

        steps = self.state_manager.get_workflow_steps(workflow.id)
        next_step = None
        for step in steps:
            if step.status == WorkflowStatus.PENDING:
                next_step = step
                break

        if not next_step:
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)
            self.session.commit()
            return {"status": "completed", "message": "Workflow completed"}

        next_step.status = WorkflowStatus.IN_PROGRESS
        next_step.started_at = datetime.utcnow()
        self.session.add(next_step)
        self.session.commit()

        result = await self._execute_step(next_step, project_id)

        if result.get("status") == "success":
            next_step.status = WorkflowStatus.COMPLETED
            next_step.completed_at = datetime.utcnow()
            next_step.output_data = str(result)
        else:
            next_step.status = WorkflowStatus.FAILED
            next_step.error_message = result.get("error", "Unknown error")

        self.session.add(next_step)
        self.session.commit()

        return result

    async def _execute_step(self, step: WorkflowStep, project_id: int) -> dict[str, Any]:
        step_to_task_type = {
            WorkflowStepType.INTERPRET_REQUIREMENT: TaskType.PLANNING,
            WorkflowStepType.CREATE_PLAN: TaskType.PLANNING,
            WorkflowStepType.VALIDATE_PLAN: TaskType.PLANNING,
            WorkflowStepType.GENERATE_CODE: TaskType.BACKEND,
            WorkflowStepType.CREATE_TESTS: TaskType.TESTING,
            WorkflowStepType.RUN_TESTS: TaskType.TESTING,
            WorkflowStepType.BUILD: TaskType.DEPLOYMENT,
            WorkflowStepType.DEPLOY: TaskType.DEPLOYMENT,
            WorkflowStepType.MONITOR: TaskType.DEPLOYMENT,
            WorkflowStepType.ROLLBACK: TaskType.DEPLOYMENT,
            WorkflowStepType.UX_REVIEW: TaskType.UX_REVIEW,
            WorkflowStepType.UI_REFINEMENT: TaskType.UI_REFINEMENT,
        }

        task_type = step_to_task_type.get(step.step_type)
        if not task_type:
            return {"status": "error", "error": f"Unknown step type: {step.step_type}"}

        tasks = self.session.exec(
            select(Task).where(
                Task.project_id == project_id,
                Task.task_type == task_type,
                Task.status == TaskStatus.PENDING,
            )
        ).all()

        if not tasks:
            return {"status": "success", "message": f"No pending tasks for {task_type}"}

        task = tasks[0]
        agent = self.get_agent_for_task(task)
        if not agent:
            return {"status": "error", "error": f"No agent available for task type: {task_type}"}

        return await agent.execute(task)

    async def rollback(self, project_id: int) -> dict[str, Any]:
        project = self.session.get(Project, project_id)
        if not project:
            return {"status": "error", "message": "Project not found"}

        self.state_manager.update_project_status(project_id, ProjectStatus.ROLLED_BACK)

        return {
            "status": "success",
            "message": f"Project {project.name} rolled back",
        }

    def get_project_status(self, project_id: int) -> dict[str, Any]:
        return self.state_manager.get_project_state(project_id)
