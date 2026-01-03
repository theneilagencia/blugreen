"""
Diagnostics Service - Handles quality diagnosis for projects.

This service implements the workflow for diagnosing project quality:
1. Run diagnostics (code quality, linting)
2. Security review (vulnerability scanning)
3. Quality assessment (UX/UI quality evaluation)
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from app.agents import InfraAgent, QAAgent, UIRefinementAgent, UXAgent
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType

logger = logging.getLogger(__name__)

WORKSPACE_BASE = Path("/tmp/blugreen_workspaces")


class DiagnosticsService:
    """Service for running quality diagnostics on projects."""

    def __init__(self, session: Session):
        self.session = session
        self._agents = self._initialize_agents()

    def _initialize_agents(self) -> dict[str, Any]:
        return {
            "qa": QAAgent(self.session),
            "infra": InfraAgent(self.session),
            "ux": UXAgent(self.session),
            "ui_refinement": UIRefinementAgent(self.session),
        }

    async def run_diagnostics(self, project: Project) -> dict[str, Any]:
        """
        Run comprehensive diagnostics on a project.

        This method analyzes code quality, security, and UX/UI quality.
        """
        logger.info(f"Starting diagnostics for project: {project.name}")

        project.status = ProjectStatus.DIAGNOSING
        self.session.add(project)
        self.session.commit()

        workflow = self._create_workflow(project)
        results: dict[str, Any] = {
            "project_id": project.id,
            "workflow_id": workflow.id,
            "steps": [],
            "summary": {},
        }

        try:
            step_result = await self._step_run_diagnostics(workflow, project)
            results["steps"].append(step_result)
            results["summary"]["code_quality"] = step_result.get("result", {})

            step_result = await self._step_security_review(workflow, project)
            results["steps"].append(step_result)
            results["summary"]["security"] = step_result.get("result", {})

            step_result = await self._step_quality_assessment(workflow, project)
            results["steps"].append(step_result)
            results["summary"]["quality"] = step_result.get("result", {})

            all_passed = all(step.get("success", False) for step in results["steps"])

            workflow.status = (
                WorkflowStatus.COMPLETED if all_passed else WorkflowStatus.FAILED
            )
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)

            project.status = ProjectStatus.DRAFT
            self.session.add(project)
            self.session.commit()

            results["status"] = "success" if all_passed else "completed_with_issues"
            results["all_passed"] = all_passed
            results["message"] = (
                "Diagnostics completed successfully"
                if all_passed
                else "Diagnostics completed with issues found"
            )
            logger.info(f"Diagnostics completed for project: {project.name}")

            return results

        except Exception as e:
            logger.error(f"Diagnostics failed: {e}")
            return await self._handle_workflow_failure(workflow, project, results, str(e))

    def _create_workflow(self, project: Project) -> Workflow:
        """Create a new workflow for the diagnostics process."""
        workflow = Workflow(
            name=f"Diagnostics - {project.name}",
            project_id=project.id,
            status=WorkflowStatus.IN_PROGRESS,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = [
            WorkflowStepType.RUN_DIAGNOSTICS,
            WorkflowStepType.SECURITY_REVIEW,
            WorkflowStepType.QUALITY_ASSESSMENT,
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

    async def _step_run_diagnostics(
        self, workflow: Workflow, project: Project
    ) -> dict[str, Any]:
        """Step 1: Run code quality diagnostics."""
        step = self._get_workflow_step(workflow, WorkflowStepType.RUN_DIAGNOSTICS)
        if not step:
            return {"step": "run_diagnostics", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 1: Running diagnostics for {project.name}")

        try:
            repo_path = self._get_workspace_path(project)
            diagnostics_results: dict[str, Any] = {
                "lint_results": [],
                "test_results": [],
                "issues_found": [],
            }

            if repo_path.exists():
                lint_result = self._run_lint_checks(repo_path)
                diagnostics_results["lint_results"] = lint_result

                test_result = self._run_test_checks(repo_path)
                diagnostics_results["test_results"] = test_result

            task = Task(
                project_id=project.id,
                name="Analyze Code Quality",
                description=f"""Analyze the following code quality diagnostics:

Lint Results:
{json.dumps(diagnostics_results['lint_results'], indent=2)}

Test Results:
{json.dumps(diagnostics_results['test_results'], indent=2)}

Provide a summary of code quality issues and recommendations.
""",
                task_type=TaskType.TESTING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["qa"]
            result = await agent.execute(task)

            output = {
                "diagnostics": diagnostics_results,
                "analysis": result,
            }

            has_critical_issues = any(
                r.get("has_errors", False) for r in diagnostics_results["lint_results"]
            )

            if result.get("status") == "success" and not has_critical_issues:
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
                )
                return {"step": "run_diagnostics", "success": True, "result": output}
            else:
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
                )
                return {
                    "step": "run_diagnostics",
                    "success": not has_critical_issues,
                    "result": output,
                    "issues": diagnostics_results.get("issues_found", []),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "run_diagnostics", "success": False, "error": str(e)}

    async def _step_security_review(
        self, workflow: Workflow, project: Project
    ) -> dict[str, Any]:
        """Step 2: Run security review."""
        step = self._get_workflow_step(workflow, WorkflowStepType.SECURITY_REVIEW)
        if not step:
            return {"step": "security_review", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 2: Running security review for {project.name}")

        try:
            repo_path = self._get_workspace_path(project)
            security_results: dict[str, Any] = {
                "vulnerabilities": [],
                "secrets_detected": [],
                "dependency_issues": [],
            }

            if repo_path.exists():
                secrets_check = self._check_for_secrets(repo_path)
                security_results["secrets_detected"] = secrets_check

                dependency_check = self._check_dependencies(repo_path)
                security_results["dependency_issues"] = dependency_check

            task = Task(
                project_id=project.id,
                name="Security Review",
                description=f"""Review the following security analysis:

Secrets Detected:
{json.dumps(security_results['secrets_detected'], indent=2)}

Dependency Issues:
{json.dumps(security_results['dependency_issues'], indent=2)}

Provide a security assessment and recommendations.
""",
                task_type=TaskType.INFRA,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            output = {
                "security_results": security_results,
                "analysis": result,
            }

            has_critical_issues = (
                len(security_results["secrets_detected"]) > 0
                or any(
                    d.get("severity") == "critical"
                    for d in security_results["dependency_issues"]
                )
            )

            self._update_step_status(
                step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
            )
            return {
                "step": "security_review",
                "success": not has_critical_issues,
                "result": output,
            }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "security_review", "success": False, "error": str(e)}

    async def _step_quality_assessment(
        self, workflow: Workflow, project: Project
    ) -> dict[str, Any]:
        """Step 3: Run UX/UI quality assessment."""
        step = self._get_workflow_step(workflow, WorkflowStepType.QUALITY_ASSESSMENT)
        if not step:
            return {
                "step": "quality_assessment",
                "success": False,
                "error": "Step not found",
            }

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 3: Running quality assessment for {project.name}")

        try:
            ux_task = Task(
                project_id=project.id,
                name="UX Quality Assessment",
                description="""Evaluate the UX quality of this project based on:
- Clarity
- Predictability
- Feedback
- Comprehensible errors

Provide a detailed assessment and score.
""",
                task_type=TaskType.FRONTEND,
                status=TaskStatus.PENDING,
            )
            self.session.add(ux_task)
            self.session.commit()
            self.session.refresh(ux_task)

            ux_agent = self._agents["ux"]
            ux_result = await ux_agent.execute(ux_task)

            ui_task = Task(
                project_id=project.id,
                name="UI Quality Assessment",
                description="""Evaluate the UI quality of this project based on:
- Clear visual hierarchy
- Consistent spacing
- Readability
- Adequate contrast

Provide a detailed assessment and score.
""",
                task_type=TaskType.FRONTEND,
                status=TaskStatus.PENDING,
            )
            self.session.add(ui_task)
            self.session.commit()
            self.session.refresh(ui_task)

            ui_agent = self._agents["ui_refinement"]
            ui_result = await ui_agent.execute(ui_task)

            output = {
                "ux_assessment": ux_result,
                "ui_assessment": ui_result,
            }

            ux_passed = ux_result.get("status") == "success" or ux_result.get(
                "result", {}
            ).get("all_passed", False)
            ui_passed = ui_result.get("status") == "success" or ui_result.get(
                "result", {}
            ).get("all_passed", False)

            self._update_step_status(
                step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
            )
            return {
                "step": "quality_assessment",
                "success": ux_passed and ui_passed,
                "result": output,
            }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "quality_assessment", "success": False, "error": str(e)}

    def _run_lint_checks(self, repo_path: Path) -> list[dict[str, Any]]:
        """Run lint checks on the repository."""
        results = []

        if (repo_path / "package.json").exists():
            try:
                result = subprocess.run(
                    ["npm", "run", "lint", "--if-present"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                results.append(
                    {
                        "tool": "npm lint",
                        "success": result.returncode == 0,
                        "has_errors": result.returncode != 0,
                        "output": result.stdout[:1000] if result.stdout else None,
                        "errors": result.stderr[:1000] if result.stderr else None,
                    }
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if (repo_path / "pyproject.toml").exists():
            try:
                result = subprocess.run(
                    ["poetry", "run", "ruff", "check", "."],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                results.append(
                    {
                        "tool": "ruff",
                        "success": result.returncode == 0,
                        "has_errors": result.returncode != 0,
                        "output": result.stdout[:1000] if result.stdout else None,
                        "errors": result.stderr[:1000] if result.stderr else None,
                    }
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return results

    def _run_test_checks(self, repo_path: Path) -> list[dict[str, Any]]:
        """Run test checks on the repository."""
        results = []

        if (repo_path / "package.json").exists():
            try:
                result = subprocess.run(
                    ["npm", "test", "--if-present"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results.append(
                    {
                        "tool": "npm test",
                        "success": result.returncode == 0,
                        "output": result.stdout[:1000] if result.stdout else None,
                        "errors": result.stderr[:1000] if result.stderr else None,
                    }
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        if (repo_path / "pyproject.toml").exists():
            try:
                result = subprocess.run(
                    ["poetry", "run", "pytest", "-v", "--tb=short"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                results.append(
                    {
                        "tool": "pytest",
                        "success": result.returncode == 0,
                        "output": result.stdout[:1000] if result.stdout else None,
                        "errors": result.stderr[:1000] if result.stderr else None,
                    }
                )
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return results

    def _check_for_secrets(self, repo_path: Path) -> list[dict[str, Any]]:
        """Check for exposed secrets in the repository."""
        secrets_found = []
        secret_patterns = [
            ".env",
            "credentials.json",
            "secrets.json",
            ".aws/credentials",
            "id_rsa",
            "id_ed25519",
        ]

        for pattern in secret_patterns:
            secret_path = repo_path / pattern
            if secret_path.exists() and secret_path.is_file():
                secrets_found.append(
                    {
                        "file": pattern,
                        "severity": "high",
                        "message": f"Potential secret file found: {pattern}",
                    }
                )

        return secrets_found

    def _check_dependencies(self, repo_path: Path) -> list[dict[str, Any]]:
        """Check for dependency issues."""
        issues = []

        if (repo_path / "package-lock.json").exists():
            try:
                result = subprocess.run(
                    ["npm", "audit", "--json"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=60,
                )
                if result.returncode != 0:
                    try:
                        audit_data = json.loads(result.stdout)
                        vulnerabilities = audit_data.get("vulnerabilities", {})
                        for name, vuln in vulnerabilities.items():
                            issues.append(
                                {
                                    "package": name,
                                    "severity": vuln.get("severity", "unknown"),
                                    "message": vuln.get("via", [{}])[0].get("title", "")
                                    if isinstance(vuln.get("via"), list)
                                    else str(vuln.get("via")),
                                }
                            )
                    except json.JSONDecodeError:
                        pass
            except (subprocess.TimeoutExpired, FileNotFoundError):
                pass

        return issues

    async def _handle_workflow_failure(
        self,
        workflow: Workflow,
        project: Project,
        results: dict[str, Any],
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Handle workflow failure."""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.utcnow()
        self.session.add(workflow)

        project.status = ProjectStatus.FAILED
        self.session.add(project)
        self.session.commit()

        results["status"] = "failed"
        results["error"] = error or "Workflow failed"
        logger.error(f"Diagnostics failed for {project.name}: {error}")

        return results

    def get_latest_diagnostics(self, project: Project) -> Optional[dict[str, Any]]:
        """Get the latest diagnostics results for a project."""
        workflow = self.session.exec(
            select(Workflow)
            .where(Workflow.project_id == project.id)
            .where(Workflow.name.startswith("Diagnostics"))
            .order_by(Workflow.created_at.desc())
        ).first()

        if not workflow:
            return None

        results: dict[str, Any] = {
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "created_at": workflow.created_at.isoformat(),
            "steps": {},
        }

        for step_type in [
            WorkflowStepType.RUN_DIAGNOSTICS,
            WorkflowStepType.SECURITY_REVIEW,
            WorkflowStepType.QUALITY_ASSESSMENT,
        ]:
            step = self._get_workflow_step(workflow, step_type)
            if step:
                step_data: dict[str, Any] = {
                    "status": step.status.value,
                }
                if step.output_data:
                    try:
                        step_data["output"] = json.loads(step.output_data)
                    except json.JSONDecodeError:
                        step_data["output"] = step.output_data
                if step.error_message:
                    step_data["error"] = step.error_message
                results["steps"][step_type.value] = step_data

        return results
