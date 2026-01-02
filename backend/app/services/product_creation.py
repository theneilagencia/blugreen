"""
Product Creation Service - Orchestrates the complete product creation workflow.

This service implements the 10-step autonomous workflow defined in WORKFLOWS.md:
1. Interpret requirement
2. Create technical plan
3. Validate plan with rules
4. Generate code
5. Create tests
6. Run tests
7. Build
8. Deploy to production
9. Monitor
10. Rollback if necessary
"""

import json
import logging
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
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType

logger = logging.getLogger(__name__)


class ProductCreationService:
    """Service for creating products from zero using the autonomous workflow."""

    def __init__(self, session: Session):
        self.session = session
        self._agents = self._initialize_agents()

    def _initialize_agents(self) -> dict[str, Any]:
        return {
            "architect": ArchitectAgent(self.session),
            "backend": BackendAgent(self.session),
            "frontend": FrontendAgent(self.session),
            "infra": InfraAgent(self.session),
            "qa": QAAgent(self.session),
            "ux": UXAgent(self.session),
            "ui_refinement": UIRefinementAgent(self.session),
        }

    async def create_product(
        self,
        project: Project,
        requirements: str,
    ) -> dict[str, Any]:
        """
        Create a complete product from requirements.

        This method orchestrates the entire product creation workflow,
        executing each step in sequence and handling failures with rollback.
        """
        logger.info(f"Starting product creation for project: {project.name}")

        workflow = self._create_workflow(project)
        results: dict[str, Any] = {
            "project_id": project.id,
            "workflow_id": workflow.id,
            "steps": [],
        }

        try:
            project.status = ProjectStatus.PLANNING
            self.session.add(project)
            self.session.commit()

            step_result = await self._step_interpret_requirement(workflow, project, requirements)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_create_plan(workflow, project, requirements)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_validate_plan(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            project.status = ProjectStatus.IN_PROGRESS
            self.session.add(project)
            self.session.commit()

            step_result = await self._step_generate_code(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_create_tests(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            project.status = ProjectStatus.TESTING
            self.session.add(project)
            self.session.commit()

            step_result = await self._step_run_tests(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_build(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            project.status = ProjectStatus.DEPLOYING
            self.session.add(project)
            self.session.commit()

            step_result = await self._step_deploy(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_monitor(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)

            project.status = ProjectStatus.DEPLOYED
            self.session.add(project)
            self.session.commit()

            results["status"] = "success"
            results["message"] = "Product created successfully"
            logger.info(f"Product creation completed for project: {project.name}")

            return results

        except Exception as e:
            logger.error(f"Product creation failed: {e}")
            return await self._handle_workflow_failure(workflow, project, results, str(e))

    def _create_workflow(self, project: Project) -> Workflow:
        """Create a new workflow for the product creation process."""
        workflow = Workflow(
            name=f"Product Creation - {project.name}",
            project_id=project.id,
            status=WorkflowStatus.IN_PROGRESS,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = [
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

        for order, step_type in enumerate(steps):
            step = WorkflowStep(
                workflow_id=workflow.id,
                step_type=step_type,
                status=WorkflowStatus.PENDING,
                order=order,
            )
            self.session.add(step)

        self.session.commit()
        return workflow

    def _get_workflow_step(
        self, workflow: Workflow, step_type: WorkflowStepType
    ) -> Optional[WorkflowStep]:
        """Get a specific workflow step by type."""
        return self.session.exec(
            select(WorkflowStep).where(
                WorkflowStep.workflow_id == workflow.id,
                WorkflowStep.step_type == step_type,
            )
        ).first()

    def _update_step_status(
        self,
        step: WorkflowStep,
        status: WorkflowStatus,
        output_data: Optional[str] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update the status of a workflow step."""
        step.status = status
        if status == WorkflowStatus.IN_PROGRESS:
            step.started_at = datetime.utcnow()
        elif status in [WorkflowStatus.COMPLETED, WorkflowStatus.FAILED]:
            step.completed_at = datetime.utcnow()
        if output_data:
            step.output_data = output_data
        if error_message:
            step.error_message = error_message
        self.session.add(step)
        self.session.commit()

    async def _step_interpret_requirement(
        self, workflow: Workflow, project: Project, requirements: str
    ) -> dict[str, Any]:
        """Step 1: Interpret the requirement using the Architect agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.INTERPRET_REQUIREMENT)
        if not step:
            return {"step": "interpret_requirement", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 1: Interpreting requirements for {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Interpret Requirements",
                description=f"Interpret and analyze the following requirements:\n\n{requirements}",
                task_type=TaskType.PLANNING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["architect"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {
                    "step": "interpret_requirement",
                    "success": True,
                    "result": result,
                }
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Unknown error"),
                )
                return {
                    "step": "interpret_requirement",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "interpret_requirement", "success": False, "error": str(e)}

    async def _step_create_plan(
        self, workflow: Workflow, project: Project, requirements: str
    ) -> dict[str, Any]:
        """Step 2: Create technical plan using the Architect agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_PLAN)
        if not step:
            return {"step": "create_plan", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 2: Creating technical plan for {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Create Technical Plan",
                description=f"Create a detailed technical plan for:\n\n{requirements}",
                task_type=TaskType.PLANNING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["architect"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "create_plan", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Unknown error"),
                )
                return {
                    "step": "create_plan",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "create_plan", "success": False, "error": str(e)}

    async def _step_validate_plan(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 3: Validate the plan against rules using QA agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.VALIDATE_PLAN)
        if not step:
            return {"step": "validate_plan", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 3: Validating plan for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_PLAN)
            plan_data = prev_step.output_data if prev_step else "{}"

            task = Task(
                project_id=project.id,
                name="Validate Technical Plan",
                description=f"Validate the following technical plan:\n\n{plan_data}",
                task_type=TaskType.TESTING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["qa"]
            result = await agent.execute(task)

            if result.get("status") == "success" or result.get("result", {}).get(
                "all_passed", False
            ):
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "validate_plan", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Validation failed"),
                )
                return {
                    "step": "validate_plan",
                    "success": False,
                    "error": result.get("error", "Validation failed"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "validate_plan", "success": False, "error": str(e)}

    async def _step_generate_code(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 4: Generate code using Backend and Frontend agents."""
        step = self._get_workflow_step(workflow, WorkflowStepType.GENERATE_CODE)
        if not step:
            return {"step": "generate_code", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 4: Generating code for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_PLAN)
            plan_data = prev_step.output_data if prev_step else "{}"

            backend_task = Task(
                project_id=project.id,
                name="Generate Backend Code",
                description=f"Generate backend code based on plan:\n\n{plan_data}",
                task_type=TaskType.BACKEND,
                status=TaskStatus.PENDING,
            )
            self.session.add(backend_task)
            self.session.commit()
            self.session.refresh(backend_task)

            backend_agent = self._agents["backend"]
            backend_result = await backend_agent.execute(backend_task)

            frontend_task = Task(
                project_id=project.id,
                name="Generate Frontend Code",
                description=f"Generate frontend code based on plan:\n\n{plan_data}",
                task_type=TaskType.FRONTEND,
                status=TaskStatus.PENDING,
            )
            self.session.add(frontend_task)
            self.session.commit()
            self.session.refresh(frontend_task)

            frontend_agent = self._agents["frontend"]
            frontend_result = await frontend_agent.execute(frontend_task)

            combined_result = {
                "backend": backend_result,
                "frontend": frontend_result,
            }

            backend_success = backend_result.get("status") == "success"
            frontend_success = frontend_result.get("status") == "success"

            if backend_success and frontend_success:
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(combined_result)
                )
                return {"step": "generate_code", "success": True, "result": combined_result}
            else:
                errors = []
                if not backend_success:
                    errors.append(f"Backend: {backend_result.get('error', 'Failed')}")
                if not frontend_success:
                    errors.append(f"Frontend: {frontend_result.get('error', 'Failed')}")
                error_msg = "; ".join(errors)
                self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
                return {"step": "generate_code", "success": False, "error": error_msg}

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "generate_code", "success": False, "error": str(e)}

    async def _step_create_tests(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 5: Create tests using Backend agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_TESTS)
        if not step:
            return {"step": "create_tests", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 5: Creating tests for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.GENERATE_CODE)
            code_data = prev_step.output_data if prev_step else "{}"

            task = Task(
                project_id=project.id,
                name="Create Tests",
                description=f"Create tests for the generated code:\n\n{code_data}",
                task_type=TaskType.BACKEND,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["backend"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "create_tests", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Unknown error"),
                )
                return {
                    "step": "create_tests",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "create_tests", "success": False, "error": str(e)}

    async def _step_run_tests(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 6: Run tests using QA agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.RUN_TESTS)
        if not step:
            return {"step": "run_tests", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 6: Running tests for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_TESTS)
            tests_data = prev_step.output_data if prev_step else "{}"

            task = Task(
                project_id=project.id,
                name="Run Tests",
                description=f"Run and validate tests:\n\n{tests_data}",
                task_type=TaskType.TESTING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["qa"]
            result = await agent.execute(task)

            all_passed = result.get("result", {}).get("all_passed", False)
            if result.get("status") == "success" or all_passed:
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "run_tests", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Tests failed"),
                )
                return {
                    "step": "run_tests",
                    "success": False,
                    "error": result.get("error", "Tests failed"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "run_tests", "success": False, "error": str(e)}

    async def _step_build(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 7: Build the project using Infra agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.BUILD)
        if not step:
            return {"step": "build", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 7: Building project {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Build Project",
                description=f"Build Docker images and prepare deployment for project: {project.name}",
                task_type=TaskType.DEPLOYMENT,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "build", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Build failed"),
                )
                return {
                    "step": "build",
                    "success": False,
                    "error": result.get("error", "Build failed"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "build", "success": False, "error": str(e)}

    async def _step_deploy(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 8: Deploy to production using Infra agent."""
        step = self._get_workflow_step(workflow, WorkflowStepType.DEPLOY)
        if not step:
            return {"step": "deploy", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 8: Deploying project {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Deploy to Production",
                description=f"Deploy project {project.name} to production via Coolify",
                task_type=TaskType.DEPLOYMENT,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "deploy", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Deployment failed"),
                )
                return {
                    "step": "deploy",
                    "success": False,
                    "error": result.get("error", "Deployment failed"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "deploy", "success": False, "error": str(e)}

    async def _step_monitor(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 9: Monitor the deployment."""
        step = self._get_workflow_step(workflow, WorkflowStepType.MONITOR)
        if not step:
            return {"step": "monitor", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 9: Monitoring deployment for {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Monitor Deployment",
                description=f"Monitor deployment health for project: {project.name}",
                task_type=TaskType.DEPLOYMENT,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(result)
                )
                return {"step": "monitor", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Monitoring failed"),
                )
                return {
                    "step": "monitor",
                    "success": False,
                    "error": result.get("error", "Monitoring failed"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "monitor", "success": False, "error": str(e)}

    async def _handle_workflow_failure(
        self,
        workflow: Workflow,
        project: Project,
        results: dict[str, Any],
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Handle workflow failure and trigger rollback."""
        logger.warning(f"Workflow failed for project {project.name}, initiating rollback")

        workflow.status = WorkflowStatus.FAILED
        self.session.add(workflow)

        project.status = ProjectStatus.FAILED
        self.session.add(project)
        self.session.commit()

        rollback_result = await self.rollback(workflow, project)

        results["status"] = "failed"
        results["error"] = error or "Workflow failed"
        results["rollback"] = rollback_result

        return results

    async def rollback(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """
        Rollback the deployment.

        Step 10: Automatic rollback if any step fails.
        """
        logger.info(f"Rolling back project {project.name}")

        try:
            task = Task(
                project_id=project.id,
                name="Rollback Deployment",
                description=f"Rollback deployment for project: {project.name}",
                task_type=TaskType.DEPLOYMENT,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            workflow.status = WorkflowStatus.ROLLED_BACK
            self.session.add(workflow)

            project.status = ProjectStatus.ROLLED_BACK
            self.session.add(project)
            self.session.commit()

            return {
                "status": "rolled_back",
                "message": f"Project {project.name} rolled back successfully",
                "result": result,
            }

        except Exception as e:
            logger.error(f"Rollback failed: {e}")
            return {
                "status": "rollback_failed",
                "error": str(e),
            }
