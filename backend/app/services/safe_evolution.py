"""
Safe Evolution Service - Handles safe project evolution with rollback capability.

This service implements the workflow for safely evolving projects:
1. Create baseline (capture current state)
2. Create changeset (plan changes)
3. Apply changes (implement with validation)
4. Run tests and build
5. Deploy with rollback capability
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from app.agents import (
    ArchitectAgent,
    BackendAgent,
    FrontendAgent,
    InfraAgent,
    QAAgent,
)
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType
from app.services.deployment import get_deployment_service

logger = logging.getLogger(__name__)

WORKSPACE_BASE = Path("/tmp/blugreen_workspaces")


class SafeEvolutionService:
    """Service for safely evolving projects with rollback capability."""

    def __init__(self, session: Session):
        self.session = session
        self._agents = self._initialize_agents()
        self._deployment_service = get_deployment_service()

    def _initialize_agents(self) -> dict[str, Any]:
        return {
            "architect": ArchitectAgent(self.session),
            "backend": BackendAgent(self.session),
            "frontend": FrontendAgent(self.session),
            "infra": InfraAgent(self.session),
            "qa": QAAgent(self.session),
        }

    async def evolve_project(
        self,
        project: Project,
        change_request: str,
    ) -> dict[str, Any]:
        """
        Safely evolve a project based on a change request.

        This method creates a baseline, plans changes, implements them,
        and deploys with automatic rollback on failure.
        """
        logger.info(f"Starting safe evolution for project: {project.name}")

        project.status = ProjectStatus.EVOLVING
        self.session.add(project)
        self.session.commit()

        workflow = self._create_workflow(project)
        results: dict[str, Any] = {
            "project_id": project.id,
            "workflow_id": workflow.id,
            "change_request": change_request,
            "steps": [],
        }

        try:
            step_result = await self._step_create_baseline(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_create_changeset(workflow, project, change_request)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_validate_plan(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_apply_changes(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_rollback(workflow, project, results)

            step_result = await self._step_run_tests(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_rollback(workflow, project, results)

            step_result = await self._step_build(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_rollback(workflow, project, results)

            step_result = await self._step_deploy(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_rollback(workflow, project, results)

            step_result = await self._step_monitor(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_rollback(workflow, project, results)

            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)

            project.status = ProjectStatus.DEPLOYED
            self.session.add(project)
            self.session.commit()

            results["status"] = "success"
            results["message"] = "Project evolved successfully"
            logger.info(f"Safe evolution completed for project: {project.name}")

            return results

        except Exception as e:
            logger.error(f"Safe evolution failed: {e}")
            return await self._handle_rollback(workflow, project, results, str(e))

    def _create_workflow(self, project: Project) -> Workflow:
        """Create a new workflow for the safe evolution process."""
        workflow = Workflow(
            name=f"Safe Evolution - {project.name}",
            project_id=project.id,
            status=WorkflowStatus.IN_PROGRESS,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = [
            WorkflowStepType.CREATE_BASELINE,
            WorkflowStepType.CREATE_CHANGESET,
            WorkflowStepType.VALIDATE_PLAN,
            WorkflowStepType.APPLY_CHANGES,
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

    def _get_workspace_path(self, project: Project) -> Path:
        """Get the workspace path for a project."""
        return WORKSPACE_BASE / f"project_{project.id}" / "repo"

    async def _step_create_baseline(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 1: Create a baseline of the current state."""
        step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_BASELINE)
        if not step:
            return {"step": "create_baseline", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 1: Creating baseline for {project.name}")

        try:
            repo_path = self._get_workspace_path(project)
            baseline: dict[str, Any] = {
                "timestamp": datetime.utcnow().isoformat(),
                "project_id": project.id,
                "project_name": project.name,
            }

            if repo_path.exists():
                result = subprocess.run(
                    ["git", "rev-parse", "HEAD"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    baseline["git_sha"] = result.stdout.strip()

                result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    baseline["git_branch"] = result.stdout.strip()

            deployment_status = await self._deployment_service.get_deployment_status(project.name)
            baseline["deployment_status"] = deployment_status

            self._update_step_status(
                step, WorkflowStatus.COMPLETED, output_data=json.dumps(baseline)
            )
            return {"step": "create_baseline", "success": True, "result": baseline}

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "create_baseline", "success": False, "error": str(e)}

    async def _step_create_changeset(
        self, workflow: Workflow, project: Project, change_request: str
    ) -> dict[str, Any]:
        """Step 2: Create a changeset based on the change request."""
        step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_CHANGESET)
        if not step:
            return {"step": "create_changeset", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 2: Creating changeset for {project.name}")

        try:
            task = Task(
                project_id=project.id,
                title="Create Change Plan",
                description=f"""Create a detailed change plan for the following request:

{change_request}

The plan should include:
1. Files to be modified
2. New files to be created
3. Dependencies to be added/updated
4. Tests to be added/modified
5. Potential risks and mitigations
""",
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
                return {"step": "create_changeset", "success": True, "result": result}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Failed to create changeset"),
                )
                return {
                    "step": "create_changeset",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "create_changeset", "success": False, "error": str(e)}

    async def _step_validate_plan(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 3: Validate the change plan."""
        step = self._get_workflow_step(workflow, WorkflowStepType.VALIDATE_PLAN)
        if not step:
            return {"step": "validate_plan", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 3: Validating plan for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_CHANGESET)
            changeset_data = prev_step.output_data if prev_step else "{}"

            task = Task(
                project_id=project.id,
                title="Validate Change Plan",
                description=f"""Validate the following change plan:

{changeset_data}

Check for:
1. Compliance with project constraints
2. No destructive operations
3. Tests are included
4. No security vulnerabilities introduced
5. Backward compatibility
""",
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

    async def _step_apply_changes(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 4: Apply the changes."""
        step = self._get_workflow_step(workflow, WorkflowStepType.APPLY_CHANGES)
        if not step:
            return {"step": "apply_changes", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 4: Applying changes for {project.name}")

        try:
            prev_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_CHANGESET)
            changeset_data = prev_step.output_data if prev_step else "{}"

            backend_task = Task(
                project_id=project.id,
                title="Apply Backend Changes",
                description=f"""Apply the backend changes from the plan:

{changeset_data}
""",
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
                title="Apply Frontend Changes",
                description=f"""Apply the frontend changes from the plan:

{changeset_data}
""",
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
                return {"step": "apply_changes", "success": True, "result": combined_result}
            else:
                errors = []
                if not backend_success:
                    errors.append(f"Backend: {backend_result.get('error', 'Failed')}")
                if not frontend_success:
                    errors.append(f"Frontend: {frontend_result.get('error', 'Failed')}")
                error_msg = "; ".join(errors)
                self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
                return {"step": "apply_changes", "success": False, "error": error_msg}

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "apply_changes", "success": False, "error": str(e)}

    async def _step_run_tests(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step 5: Run tests to verify changes."""
        step = self._get_workflow_step(workflow, WorkflowStepType.RUN_TESTS)
        if not step:
            return {"step": "run_tests", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 5: Running tests for {project.name}")

        try:
            task = Task(
                project_id=project.id,
                title="Run Tests",
                description="Run all tests to verify the changes work correctly.",
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
        """Step 6: Build the project."""
        step = self._get_workflow_step(workflow, WorkflowStepType.BUILD)
        if not step:
            return {"step": "build", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 6: Building {project.name}")

        try:
            task = Task(
                project_id=project.id,
                title="Build Project",
                description="Build the project for deployment.",
                task_type=TaskType.INFRA,
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
        """Step 7: Deploy the changes."""
        step = self._get_workflow_step(workflow, WorkflowStepType.DEPLOY)
        if not step:
            return {"step": "deploy", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 7: Deploying {project.name}")

        try:
            result = await self._deployment_service.deploy(
                project_name=project.name,
                docker_image=f"{project.name}:latest",
                environment_variables={},
            )

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
        """Step 8: Monitor the deployment."""
        step = self._get_workflow_step(workflow, WorkflowStepType.MONITOR)
        if not step:
            return {"step": "monitor", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 8: Monitoring {project.name}")

        try:
            task = Task(
                project_id=project.id,
                title="Monitor Deployment",
                description="Monitor the deployment for any issues.",
                task_type=TaskType.INFRA,
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
                    error_message=result.get("error", "Monitoring detected issues"),
                )
                return {
                    "step": "monitor",
                    "success": False,
                    "error": result.get("error", "Monitoring detected issues"),
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
        """Handle workflow failure without rollback."""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.utcnow()
        self.session.add(workflow)

        project.status = ProjectStatus.FAILED
        self.session.add(project)
        self.session.commit()

        results["status"] = "failed"
        results["error"] = error or "Workflow failed"
        logger.error(f"Safe evolution failed for {project.name}: {error}")

        return results

    async def _handle_rollback(
        self,
        workflow: Workflow,
        project: Project,
        results: dict[str, Any],
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Handle rollback to baseline."""
        logger.info(f"Initiating rollback for {project.name}")

        baseline_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_BASELINE)
        if baseline_step and baseline_step.output_data:
            try:
                baseline = json.loads(baseline_step.output_data)

                repo_path = self._get_workspace_path(project)
                if repo_path.exists() and baseline.get("git_sha"):
                    subprocess.run(
                        ["git", "checkout", baseline["git_sha"]],
                        cwd=repo_path,
                        capture_output=True,
                        timeout=60,
                    )

                rollback_result = await self._deployment_service.rollback(project.name)
                results["rollback"] = rollback_result

            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
                results["rollback_error"] = str(rollback_error)

        workflow.status = WorkflowStatus.ROLLED_BACK
        workflow.completed_at = datetime.utcnow()
        self.session.add(workflow)

        project.status = ProjectStatus.ROLLED_BACK
        self.session.add(project)
        self.session.commit()

        results["status"] = "rolled_back"
        results["error"] = error or "Changes rolled back due to failure"
        logger.info(f"Rollback completed for {project.name}")

        return results

    async def rollback_to_baseline(self, project: Project) -> dict[str, Any]:
        """Manually rollback a project to its last baseline."""
        logger.info(f"Manual rollback requested for {project.name}")

        workflow = self.session.exec(
            select(Workflow)
            .where(Workflow.project_id == project.id)
            .where(Workflow.name.startswith("Safe Evolution"))
            .order_by(Workflow.created_at.desc())
        ).first()

        if not workflow:
            return {
                "status": "failed",
                "error": "No evolution workflow found for rollback",
            }

        baseline_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_BASELINE)
        if not baseline_step or not baseline_step.output_data:
            return {"status": "failed", "error": "No baseline found for rollback"}

        try:
            baseline = json.loads(baseline_step.output_data)

            repo_path = self._get_workspace_path(project)
            if repo_path.exists() and baseline.get("git_sha"):
                subprocess.run(
                    ["git", "checkout", baseline["git_sha"]],
                    cwd=repo_path,
                    capture_output=True,
                    timeout=60,
                )

            rollback_result = await self._deployment_service.rollback(project.name)

            project.status = ProjectStatus.ROLLED_BACK
            self.session.add(project)
            self.session.commit()

            return {
                "status": "success",
                "message": "Rolled back to baseline",
                "baseline": baseline,
                "deployment_rollback": rollback_result,
            }

        except Exception as e:
            logger.error(f"Manual rollback failed: {e}")
            return {"status": "failed", "error": str(e)}

    def get_evolution_history(self, project: Project) -> list[dict[str, Any]]:
        """Get the evolution history for a project."""
        workflows = self.session.exec(
            select(Workflow)
            .where(Workflow.project_id == project.id)
            .where(Workflow.name.startswith("Safe Evolution"))
            .order_by(Workflow.created_at.desc())
        ).all()

        history = []
        for workflow in workflows:
            entry: dict[str, Any] = {
                "workflow_id": workflow.id,
                "status": workflow.status.value,
                "created_at": workflow.created_at.isoformat(),
                "completed_at": (
                    workflow.completed_at.isoformat() if workflow.completed_at else None
                ),
            }

            changeset_step = self._get_workflow_step(workflow, WorkflowStepType.CREATE_CHANGESET)
            if changeset_step and changeset_step.output_data:
                try:
                    changeset = json.loads(changeset_step.output_data)
                    entry["changeset_summary"] = changeset.get("result", {}).get("output", "")[:200]
                except json.JSONDecodeError:
                    pass

            history.append(entry)

        return history
