"""
Project Assumption Service - Handles assuming existing repositories.

This service implements the workflow for taking over existing projects:
1. Fetch repository (clone/pull)
2. Index codebase (analyze structure)
3. Detect stack (identify technologies and build commands)
"""

import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from app.agents import ArchitectAgent, BackendAgent, FrontendAgent, InfraAgent, QAAgent
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType

logger = logging.getLogger(__name__)

WORKSPACE_BASE = Path("/tmp/blugreen_workspaces")


class ProjectAssumptionService:
    """Service for assuming existing repositories."""

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
        }

    async def assume_project(
        self,
        project: Project,
        repository_url: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """
        Assume an existing repository.

        This method clones the repository, analyzes its structure,
        and detects the technology stack.
        """
        logger.info(f"Starting project assumption for: {repository_url}")

        project.repository_url = repository_url
        project.status = ProjectStatus.ASSUMING
        self.session.add(project)
        self.session.commit()

        workflow = self._create_workflow(project)
        results: dict[str, Any] = {
            "project_id": project.id,
            "workflow_id": workflow.id,
            "repository_url": repository_url,
            "branch": branch,
            "steps": [],
        }

        try:
            step_result = await self._step_fetch_repository(
                workflow, project, repository_url, branch
            )
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_index_codebase(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            step_result = await self._step_detect_stack(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)

            project.status = ProjectStatus.DRAFT
            self.session.add(project)
            self.session.commit()

            results["status"] = "success"
            results["message"] = "Project assumed successfully"
            logger.info(f"Project assumption completed for: {project.name}")

            return results

        except Exception as e:
            logger.error(f"Project assumption failed: {e}")
            return await self._handle_workflow_failure(workflow, project, results, str(e))

    def _create_workflow(self, project: Project) -> Workflow:
        """Create a new workflow for the project assumption process."""
        workflow = Workflow(
            name=f"Project Assumption - {project.name}",
            project_id=project.id,
            status=WorkflowStatus.IN_PROGRESS,
        )
        self.session.add(workflow)
        self.session.commit()
        self.session.refresh(workflow)

        steps = [
            WorkflowStepType.FETCH_REPOSITORY,
            WorkflowStepType.INDEX_CODEBASE,
            WorkflowStepType.DETECT_STACK,
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
        workspace = WORKSPACE_BASE / f"project_{project.id}"
        workspace.mkdir(parents=True, exist_ok=True)
        return workspace

    async def _step_fetch_repository(
        self,
        workflow: Workflow,
        project: Project,
        repository_url: str,
        branch: str,
    ) -> dict[str, Any]:
        """Step 1: Fetch the repository (clone or pull)."""
        step = self._get_workflow_step(workflow, WorkflowStepType.FETCH_REPOSITORY)
        if not step:
            return {"step": "fetch_repository", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 1: Fetching repository {repository_url}")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            if repo_path.exists():
                result = subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
            else:
                result = subprocess.run(
                    ["git", "clone", "--branch", branch, repository_url, str(repo_path)],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )

            if result.returncode != 0:
                error_msg = result.stderr or "Git operation failed"
                self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
                return {"step": "fetch_repository", "success": False, "error": error_msg}

            output = {
                "repository_url": repository_url,
                "branch": branch,
                "local_path": str(repo_path),
                "git_output": result.stdout,
            }

            self._update_step_status(
                step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
            )
            return {"step": "fetch_repository", "success": True, "result": output}

        except subprocess.TimeoutExpired:
            error_msg = "Git operation timed out"
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
            return {"step": "fetch_repository", "success": False, "error": error_msg}
        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "fetch_repository", "success": False, "error": str(e)}

    async def _step_index_codebase(
        self, workflow: Workflow, project: Project
    ) -> dict[str, Any]:
        """Step 2: Index the codebase (analyze structure)."""
        step = self._get_workflow_step(workflow, WorkflowStepType.INDEX_CODEBASE)
        if not step:
            return {"step": "index_codebase", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 2: Indexing codebase for {project.name}")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            file_tree = self._build_file_tree(repo_path)
            key_files = self._identify_key_files(repo_path)
            readme_content = self._read_readme(repo_path)

            task = Task(
                project_id=project.id,
                name="Analyze Codebase Structure",
                description=f"""Analyze the following codebase structure:

File Tree:
{json.dumps(file_tree, indent=2)}

Key Files Found:
{json.dumps(key_files, indent=2)}

README Content:
{readme_content[:2000] if readme_content else 'No README found'}
""",
                task_type=TaskType.PLANNING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["architect"]
            result = await agent.execute(task)

            output = {
                "file_tree": file_tree,
                "key_files": key_files,
                "readme_summary": readme_content[:500] if readme_content else None,
                "analysis": result,
            }

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
                )
                return {"step": "index_codebase", "success": True, "result": output}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Analysis failed"),
                )
                return {
                    "step": "index_codebase",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "index_codebase", "success": False, "error": str(e)}

    async def _step_detect_stack(
        self, workflow: Workflow, project: Project
    ) -> dict[str, Any]:
        """Step 3: Detect the technology stack."""
        step = self._get_workflow_step(workflow, WorkflowStepType.DETECT_STACK)
        if not step:
            return {"step": "detect_stack", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"Step 3: Detecting stack for {project.name}")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            detected_stack = self._detect_technologies(repo_path)
            build_commands = self._detect_build_commands(repo_path)
            test_commands = self._detect_test_commands(repo_path)

            task = Task(
                project_id=project.id,
                name="Analyze Technology Stack",
                description=f"""Analyze the detected technology stack:

Detected Technologies:
{json.dumps(detected_stack, indent=2)}

Build Commands:
{json.dumps(build_commands, indent=2)}

Test Commands:
{json.dumps(test_commands, indent=2)}

Provide recommendations for working with this stack.
""",
                task_type=TaskType.PLANNING,
                status=TaskStatus.PENDING,
            )
            self.session.add(task)
            self.session.commit()
            self.session.refresh(task)

            agent = self._agents["infra"]
            result = await agent.execute(task)

            output = {
                "detected_stack": detected_stack,
                "build_commands": build_commands,
                "test_commands": test_commands,
                "analysis": result,
            }

            if result.get("status") == "success":
                self._update_step_status(
                    step, WorkflowStatus.COMPLETED, output_data=json.dumps(output)
                )
                return {"step": "detect_stack", "success": True, "result": output}
            else:
                self._update_step_status(
                    step,
                    WorkflowStatus.FAILED,
                    error_message=result.get("error", "Stack detection failed"),
                )
                return {
                    "step": "detect_stack",
                    "success": False,
                    "error": result.get("error"),
                }

        except Exception as e:
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=str(e))
            return {"step": "detect_stack", "success": False, "error": str(e)}

    def _build_file_tree(self, repo_path: Path, max_depth: int = 3) -> dict[str, Any]:
        """Build a file tree representation of the repository."""
        tree: dict[str, Any] = {"name": repo_path.name, "type": "directory", "children": []}

        def add_to_tree(path: Path, current: dict, depth: int) -> None:
            if depth > max_depth:
                return
            try:
                for item in sorted(path.iterdir()):
                    if item.name.startswith(".") and item.name not in [
                        ".github",
                        ".env.example",
                    ]:
                        continue
                    if item.name in ["node_modules", "__pycache__", ".git", "venv", ".venv"]:
                        continue

                    if item.is_file():
                        current["children"].append({"name": item.name, "type": "file"})
                    elif item.is_dir():
                        subdir: dict[str, Any] = {
                            "name": item.name,
                            "type": "directory",
                            "children": [],
                        }
                        current["children"].append(subdir)
                        add_to_tree(item, subdir, depth + 1)
            except PermissionError:
                pass

        add_to_tree(repo_path, tree, 0)
        return tree

    def _identify_key_files(self, repo_path: Path) -> list[str]:
        """Identify key configuration and documentation files."""
        key_patterns = [
            "package.json",
            "pyproject.toml",
            "requirements.txt",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.yaml",
            ".env.example",
            "README.md",
            "README.rst",
            "Makefile",
            "tsconfig.json",
            "next.config.js",
            "next.config.mjs",
            "vite.config.ts",
            "webpack.config.js",
        ]

        found_files = []
        for pattern in key_patterns:
            if (repo_path / pattern).exists():
                found_files.append(pattern)

        return found_files

    def _read_readme(self, repo_path: Path) -> Optional[str]:
        """Read the README file if it exists."""
        readme_names = ["README.md", "README.rst", "README.txt", "README"]
        for name in readme_names:
            readme_path = repo_path / name
            if readme_path.exists():
                try:
                    return readme_path.read_text(encoding="utf-8")
                except Exception:
                    pass
        return None

    def _detect_technologies(self, repo_path: Path) -> dict[str, list[str]]:
        """Detect technologies used in the repository."""
        technologies: dict[str, list[str]] = {
            "languages": [],
            "frameworks": [],
            "databases": [],
            "tools": [],
        }

        if (repo_path / "package.json").exists():
            technologies["languages"].append("JavaScript/TypeScript")
            try:
                pkg = json.loads((repo_path / "package.json").read_text())
                deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}
                if "next" in deps:
                    technologies["frameworks"].append("Next.js")
                if "react" in deps:
                    technologies["frameworks"].append("React")
                if "vue" in deps:
                    technologies["frameworks"].append("Vue.js")
                if "express" in deps:
                    technologies["frameworks"].append("Express.js")
                if "fastify" in deps:
                    technologies["frameworks"].append("Fastify")
            except Exception:
                pass

        if (repo_path / "pyproject.toml").exists() or (
            repo_path / "requirements.txt"
        ).exists():
            technologies["languages"].append("Python")
            try:
                if (repo_path / "pyproject.toml").exists():
                    content = (repo_path / "pyproject.toml").read_text()
                    if "fastapi" in content.lower():
                        technologies["frameworks"].append("FastAPI")
                    if "django" in content.lower():
                        technologies["frameworks"].append("Django")
                    if "flask" in content.lower():
                        technologies["frameworks"].append("Flask")
            except Exception:
                pass

        if (repo_path / "Cargo.toml").exists():
            technologies["languages"].append("Rust")

        if (repo_path / "go.mod").exists():
            technologies["languages"].append("Go")

        if (repo_path / "Dockerfile").exists():
            technologies["tools"].append("Docker")

        if (repo_path / "docker-compose.yml").exists() or (
            repo_path / "docker-compose.yaml"
        ).exists():
            technologies["tools"].append("Docker Compose")

        return technologies

    def _detect_build_commands(self, repo_path: Path) -> list[dict[str, str]]:
        """Detect build commands from configuration files."""
        commands = []

        if (repo_path / "package.json").exists():
            try:
                pkg = json.loads((repo_path / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                if "build" in scripts:
                    commands.append({"type": "npm", "command": "npm run build"})
                if "dev" in scripts:
                    commands.append({"type": "npm", "command": "npm run dev"})
            except Exception:
                pass

        if (repo_path / "pyproject.toml").exists():
            commands.append({"type": "poetry", "command": "poetry install"})
            commands.append({"type": "poetry", "command": "poetry build"})

        if (repo_path / "Makefile").exists():
            commands.append({"type": "make", "command": "make build"})

        if (repo_path / "Dockerfile").exists():
            commands.append({"type": "docker", "command": "docker build ."})

        return commands

    def _detect_test_commands(self, repo_path: Path) -> list[dict[str, str]]:
        """Detect test commands from configuration files."""
        commands = []

        if (repo_path / "package.json").exists():
            try:
                pkg = json.loads((repo_path / "package.json").read_text())
                scripts = pkg.get("scripts", {})
                if "test" in scripts:
                    commands.append({"type": "npm", "command": "npm test"})
                if "lint" in scripts:
                    commands.append({"type": "npm", "command": "npm run lint"})
            except Exception:
                pass

        if (repo_path / "pyproject.toml").exists():
            commands.append({"type": "poetry", "command": "poetry run pytest"})
            commands.append({"type": "poetry", "command": "poetry run ruff check ."})

        if (repo_path / "Makefile").exists():
            commands.append({"type": "make", "command": "make test"})

        return commands

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
        logger.error(f"Project assumption failed for {project.name}: {error}")

        return results

    def get_project_context(self, project: Project) -> Optional[dict[str, Any]]:
        """Get the context of an assumed project."""
        workflow = self.session.exec(
            select(Workflow)
            .where(Workflow.project_id == project.id)
            .where(Workflow.name.startswith("Project Assumption"))
            .where(Workflow.status == WorkflowStatus.COMPLETED)
        ).first()

        if not workflow:
            return None

        context: dict[str, Any] = {}

        for step_type in [
            WorkflowStepType.FETCH_REPOSITORY,
            WorkflowStepType.INDEX_CODEBASE,
            WorkflowStepType.DETECT_STACK,
        ]:
            step = self._get_workflow_step(workflow, step_type)
            if step and step.output_data:
                try:
                    context[step_type.value] = json.loads(step.output_data)
                except json.JSONDecodeError:
                    context[step_type.value] = step.output_data

        return context
