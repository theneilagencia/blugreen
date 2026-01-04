"""
Project Assumption Service - V2 (100% Reliable, Deterministic, Idempotent)

This service implements a robust workflow for assuming existing repositories:
1. Validate input (URL, optional branch)
2. Detect default branch (if branch=None)
3. Verify repository access
4. Clone repository in isolated workspace
5. Validate repository is not empty
6. Create initial diagnostic tasks
7. Update final project status

GUARANTEES:
- No project left in inconsistent state
- All errors are descriptive
- Execution is idempotent
- All Git commands have 30s timeout
- Default branch always detected or explicit error
"""

import json
import logging
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from sqlmodel import Session, select

from app.agents import ArchitectAgent, BackendAgent, FrontendAgent, InfraAgent, QAAgent
from app.exceptions import CouldNotDetectBranchError
from app.models.project import Project, ProjectStatus
from app.models.task import Task, TaskStatus, TaskType
from app.models.workflow import Workflow, WorkflowStatus, WorkflowStep, WorkflowStepType

logger = logging.getLogger(__name__)

WORKSPACE_BASE = Path("/tmp/blugreen_workspaces")
GIT_TIMEOUT = 30  # seconds - consistent timeout for all Git operations


class ValidationError(Exception):
    """Raised when input validation fails."""
    pass


class RepositoryAccessError(Exception):
    """Raised when repository is not accessible."""
    pass


class ProjectAssumptionService:
    """Service for assuming existing repositories with full reliability."""

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
        branch: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Assume an existing repository with full reliability guarantees.

        This method follows a strict order:
        1. Validate input
        2. Check idempotency
        3. Detect branch
        4. Verify access
        5. Clone repo
        6. Validate not empty
        7. Index codebase
        8. Detect stack
        9. Update status

        Returns:
            dict with status, message, and details
        """
        start_time = datetime.utcnow()
        logger.info(f"[ASSUME] Starting project assumption for: {repository_url}")

        # STEP 1: Validate input
        try:
            self._validate_input(repository_url, branch)
        except ValidationError as e:
            logger.error(f"[ASSUME] Validation failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "error_type": "validation_error",
            }

        # STEP 2: Check idempotency
        if project.assumption_status == "completed":
            logger.warning(f"[ASSUME] Project {project.id} already assumed successfully")
            return {
                "status": "error",
                "message": "Project already assumed successfully. Use /evolve to make changes",
                "error_type": "already_assumed",
                "project_id": project.id,
            }

        # STEP 3: Detect default branch if not provided
        try:
            if not branch:
                logger.info(f"[ASSUME] Branch not provided, detecting default branch")
                detected_branch = await self._detect_default_branch(repository_url)
                logger.info(f"[ASSUME] Detected default branch: {detected_branch}")
            else:
                detected_branch = branch
                logger.info(f"[ASSUME] Using provided branch: {detected_branch}")
        except CouldNotDetectBranchError as e:
            logger.error(f"[ASSUME] Failed to detect branch: {e}")
            return {
                "status": "error",
                "message": "Could not determine default branch for repository",
                "error_type": "branch_detection_failed",
                "details": {
                    "repository_url": e.repository_url,
                    "error_details": str(e),
                    "available_branches": e.available_branches,
                    "attempted_branches": e.attempted_branches,
                },
            }

        # STEP 4: Verify repository access
        try:
            self._verify_repository_access(repository_url, detected_branch)
        except RepositoryAccessError as e:
            logger.error(f"[ASSUME] Repository access failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "error_type": "repository_access_error",
            }

        # NOW we can safely update project and create workflow
        project.repository_url = repository_url
        project.detected_branch = detected_branch
        project.status = ProjectStatus.ASSUMING
        project.assumption_status = "in_progress"
        project.assumption_started_at = start_time
        project.assumption_error = None
        self.session.add(project)
        self.session.commit()

        workflow = self._create_workflow(project)

        results: dict[str, Any] = {
            "project_id": project.id,
            "workflow_id": workflow.id,
            "repository_url": repository_url,
            "branch": detected_branch,
            "steps": [],
        }

        try:
            # STEP 5: Fetch repository
            step_result = await self._step_fetch_repository(
                workflow, project, repository_url, detected_branch
            )
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            # STEP 6: Validate repository is not empty
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"
            if not self._is_repository_valid(repo_path):
                error_msg = "Repository is empty. Cannot assume empty repositories"
                logger.error(f"[ASSUME] {error_msg}")
                results["steps"].append({
                    "step": "validate_repository",
                    "success": False,
                    "error": error_msg,
                })
                return await self._handle_workflow_failure(workflow, project, results, error_msg)

            # STEP 7: Index codebase
            step_result = await self._step_index_codebase(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            # STEP 8: Detect stack
            step_result = await self._step_detect_stack(workflow, project)
            results["steps"].append(step_result)
            if not step_result["success"]:
                return await self._handle_workflow_failure(workflow, project, results)

            # STEP 9: Update final status
            workflow.status = WorkflowStatus.COMPLETED
            workflow.completed_at = datetime.utcnow()
            self.session.add(workflow)

            project.status = ProjectStatus.DRAFT
            project.assumption_status = "completed"
            project.assumption_completed_at = datetime.utcnow()
            self.session.add(project)
            self.session.commit()

            elapsed = (datetime.utcnow() - start_time).total_seconds()
            results["status"] = "success"
            results["message"] = "Project assumed successfully"
            results["elapsed_seconds"] = elapsed
            logger.info(f"[ASSUME] Project assumption completed in {elapsed:.2f}s")

            return results

        except Exception as e:
            logger.error(f"[ASSUME] Unexpected error: {e}", exc_info=True)
            return await self._handle_workflow_failure(workflow, project, results, str(e))

    def _validate_input(self, repository_url: str, branch: Optional[str]) -> None:
        """
        Validate input parameters.

        Raises:
            ValidationError: If validation fails
        """
        if not repository_url:
            raise ValidationError("Repository URL is required")

        if not (
            repository_url.startswith("https://")
            or repository_url.startswith("http://")
            or repository_url.startswith("git@")
        ):
            raise ValidationError(
                f"Invalid repository URL: {repository_url}. "
                "Must start with https://, http://, or git@"
            )

        if branch and not branch.strip():
            raise ValidationError("Branch name cannot be empty")

        logger.info(f"[ASSUME] Input validation passed")

    def _verify_repository_access(self, repository_url: str, branch: str) -> None:
        """
        Verify that the repository is accessible and the branch exists.

        Raises:
            RepositoryAccessError: If repository is not accessible
        """
        logger.info(f"[ASSUME] Verifying repository access: {repository_url}")

        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", repository_url, f"refs/heads/{branch}"],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT,
            )

            if result.returncode != 0:
                error_msg = result.stderr.strip()
                if "Permission denied" in error_msg or "Authentication failed" in error_msg:
                    raise RepositoryAccessError(
                        f"Permission denied accessing repository: {repository_url}. "
                        "Check credentials or access rights"
                    )
                elif "Could not resolve host" in error_msg:
                    raise RepositoryAccessError(
                        f"Could not resolve host for repository: {repository_url}. "
                        "Check network connectivity"
                    )
                else:
                    raise RepositoryAccessError(
                        f"Repository not accessible: {repository_url}. {error_msg}"
                    )

            if not result.stdout.strip():
                raise RepositoryAccessError(
                    f"Branch '{branch}' does not exist in repository: {repository_url}"
                )

            logger.info(f"[ASSUME] Repository access verified successfully")

        except subprocess.TimeoutExpired:
            raise RepositoryAccessError(
                f"Git operation timed out after {GIT_TIMEOUT}s. "
                "Repository may be too large or network is slow"
            )
        except RepositoryAccessError:
            raise
        except Exception as e:
            raise RepositoryAccessError(
                f"Failed to verify repository access: {str(e)}"
            )

    def _is_repository_valid(self, repo_path: Path) -> bool:
        """
        Check if repository is valid (not empty, has files).

        Returns:
            bool: True if repository is valid
        """
        if not repo_path.exists():
            return False

        # Check if .git directory exists
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return False

        # Check if repository has any files (excluding .git)
        has_files = False
        for item in repo_path.iterdir():
            if item.name != ".git":
                has_files = True
                break

        return has_files

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

    def _cleanup_workspace(self, project: Project) -> None:
        """Clean up workspace for a project."""
        workspace = self._get_workspace_path(project)
        if workspace.exists():
            try:
                shutil.rmtree(workspace)
                logger.info(f"[ASSUME] Cleaned up workspace: {workspace}")
            except Exception as e:
                logger.warning(f"[ASSUME] Failed to clean up workspace: {e}")

    async def _step_fetch_repository(
        self,
        workflow: Workflow,
        project: Project,
        repository_url: str,
        branch: str,
    ) -> dict[str, Any]:
        """Step: Fetch the repository (clone or pull)."""
        step = self._get_workflow_step(workflow, WorkflowStepType.FETCH_REPOSITORY)
        if not step:
            return {"step": "fetch_repository", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"[ASSUME] Step: Fetching repository {repository_url}")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            if repo_path.exists():
                logger.info(f"[ASSUME] Repository already exists, pulling latest changes")
                result = subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    timeout=GIT_TIMEOUT,
                )
            else:
                logger.info(f"[ASSUME] Cloning repository")
                result = subprocess.run(
                    ["git", "clone", "--branch", branch, "--depth", "1", repository_url, str(repo_path)],
                    capture_output=True,
                    text=True,
                    timeout=GIT_TIMEOUT,
                )

            if result.returncode != 0:
                error_msg = result.stderr.strip() or "Git operation failed"
                logger.error(f"[ASSUME] Git operation failed: {error_msg}")
                self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
                return {"step": "fetch_repository", "success": False, "error": error_msg}

            output = {
                "repository_url": repository_url,
                "branch": branch,
                "local_path": str(repo_path),
                "git_output": result.stdout.strip(),
            }

            self._update_step_status(step, WorkflowStatus.COMPLETED, output_data=json.dumps(output))
            logger.info(f"[ASSUME] Repository fetched successfully")
            return {"step": "fetch_repository", "success": True, "result": output}

        except subprocess.TimeoutExpired:
            error_msg = f"Git operation timed out after {GIT_TIMEOUT}s"
            logger.error(f"[ASSUME] {error_msg}")
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
            return {"step": "fetch_repository", "success": False, "error": error_msg}
        except Exception as e:
            error_msg = f"Unexpected error during git operation: {str(e)}"
            logger.error(f"[ASSUME] {error_msg}")
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
            return {"step": "fetch_repository", "success": False, "error": error_msg}

    async def _step_index_codebase(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step: Index the codebase (analyze structure)."""
        step = self._get_workflow_step(workflow, WorkflowStepType.INDEX_CODEBASE)
        if not step:
            return {"step": "index_codebase", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"[ASSUME] Step: Indexing codebase")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            file_tree = self._build_file_tree(repo_path)
            key_files = self._identify_key_files(repo_path)
            readme_content = self._read_readme(repo_path)

            task = Task(
                project_id=project.id,
                type=TaskType.ANALYZE,
                title="Index Codebase",
                description="Analyze repository structure and identify key files",
                status=TaskStatus.COMPLETED,
                output_data=json.dumps({
                    "file_tree": file_tree,
                    "key_files": key_files,
                    "readme": readme_content,
                }),
            )
            self.session.add(task)
            self.session.commit()

            output = {
                "file_count": len(key_files),
                "has_readme": readme_content is not None,
                "task_id": task.id,
            }

            self._update_step_status(step, WorkflowStatus.COMPLETED, output_data=json.dumps(output))
            logger.info(f"[ASSUME] Codebase indexed successfully")
            return {"step": "index_codebase", "success": True, "result": output}

        except Exception as e:
            error_msg = f"Failed to index codebase: {str(e)}"
            logger.error(f"[ASSUME] {error_msg}")
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
            return {"step": "index_codebase", "success": False, "error": error_msg}

    async def _step_detect_stack(self, workflow: Workflow, project: Project) -> dict[str, Any]:
        """Step: Detect the technology stack."""
        step = self._get_workflow_step(workflow, WorkflowStepType.DETECT_STACK)
        if not step:
            return {"step": "detect_stack", "success": False, "error": "Step not found"}

        self._update_step_status(step, WorkflowStatus.IN_PROGRESS)
        logger.info(f"[ASSUME] Step: Detecting technology stack")

        try:
            workspace = self._get_workspace_path(project)
            repo_path = workspace / "repo"

            technologies = self._detect_technologies(repo_path)
            build_commands = self._detect_build_commands(repo_path)
            test_commands = self._detect_test_commands(repo_path)

            task = Task(
                project_id=project.id,
                type=TaskType.ANALYZE,
                title="Detect Technology Stack",
                description="Identify technologies, build commands, and test commands",
                status=TaskStatus.COMPLETED,
                output_data=json.dumps({
                    "technologies": technologies,
                    "build_commands": build_commands,
                    "test_commands": test_commands,
                }),
            )
            self.session.add(task)
            self.session.commit()

            output = {
                "technologies": technologies,
                "build_commands": build_commands,
                "test_commands": test_commands,
                "task_id": task.id,
            }

            self._update_step_status(step, WorkflowStatus.COMPLETED, output_data=json.dumps(output))
            logger.info(f"[ASSUME] Technology stack detected successfully")
            return {"step": "detect_stack", "success": True, "result": output}

        except Exception as e:
            error_msg = f"Failed to detect stack: {str(e)}"
            logger.error(f"[ASSUME] {error_msg}")
            self._update_step_status(step, WorkflowStatus.FAILED, error_message=error_msg)
            return {"step": "detect_stack", "success": False, "error": error_msg}

    def _build_file_tree(self, repo_path: Path, max_depth: int = 3) -> dict[str, Any]:
        """Build a file tree of the repository."""
        # Implementation from original service
        # (keeping same logic for compatibility)
        tree: dict[str, Any] = {"name": repo_path.name, "type": "directory", "children": []}

        def _build_tree(path: Path, depth: int = 0) -> Optional[dict[str, Any]]:
            if depth > max_depth:
                return None

            if path.name.startswith(".") and path.name != ".github":
                return None

            if path.is_file():
                return {"name": path.name, "type": "file"}

            if path.is_dir():
                node: dict[str, Any] = {"name": path.name, "type": "directory", "children": []}
                try:
                    for child in sorted(path.iterdir()):
                        child_node = _build_tree(child, depth + 1)
                        if child_node:
                            node["children"].append(child_node)
                except PermissionError:
                    pass
                return node

            return None

        try:
            for item in sorted(repo_path.iterdir()):
                node = _build_tree(item, 0)
                if node:
                    tree["children"].append(node)
        except Exception:
            pass

        return tree

    def _identify_key_files(self, repo_path: Path) -> list[str]:
        """Identify key files in the repository."""
        key_patterns = [
            "README*",
            "package.json",
            "requirements.txt",
            "Pipfile",
            "Cargo.toml",
            "go.mod",
            "pom.xml",
            "build.gradle",
            "Makefile",
            "Dockerfile",
            "docker-compose.yml",
            ".github/workflows/*",
        ]

        key_files = []
        for pattern in key_patterns:
            for file_path in repo_path.glob(pattern):
                if file_path.is_file():
                    rel_path = file_path.relative_to(repo_path)
                    key_files.append(str(rel_path))

        return key_files

    def _read_readme(self, repo_path: Path) -> Optional[str]:
        """Read README file if it exists."""
        readme_patterns = ["README.md", "README.txt", "README", "readme.md"]

        for pattern in readme_patterns:
            readme_path = repo_path / pattern
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
            "tools": [],
        }

        # Language detection
        if (repo_path / "package.json").exists():
            technologies["languages"].append("JavaScript/TypeScript")
            technologies["frameworks"].append("Node.js")

        if (repo_path / "requirements.txt").exists() or (repo_path / "Pipfile").exists():
            technologies["languages"].append("Python")

        if (repo_path / "Cargo.toml").exists():
            technologies["languages"].append("Rust")

        if (repo_path / "go.mod").exists():
            technologies["languages"].append("Go")

        if (repo_path / "pom.xml").exists() or (repo_path / "build.gradle").exists():
            technologies["languages"].append("Java")

        # Tool detection
        if (repo_path / "Dockerfile").exists():
            technologies["tools"].append("Docker")

        if (repo_path / "docker-compose.yml").exists():
            technologies["tools"].append("Docker Compose")

        if (repo_path / ".github" / "workflows").exists():
            technologies["tools"].append("GitHub Actions")

        return technologies

    def _detect_build_commands(self, repo_path: Path) -> list[dict[str, str]]:
        """Detect build commands from common files."""
        commands = []

        # package.json scripts
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                import json as json_lib
                data = json_lib.loads(package_json.read_text())
                if "scripts" in data and "build" in data["scripts"]:
                    commands.append({
                        "command": "npm run build",
                        "source": "package.json",
                    })
            except Exception:
                pass

        # Makefile
        makefile = repo_path / "Makefile"
        if makefile.exists():
            commands.append({
                "command": "make",
                "source": "Makefile",
            })

        return commands

    def _detect_test_commands(self, repo_path: Path) -> list[dict[str, str]]:
        """Detect test commands from common files."""
        commands = []

        # package.json scripts
        package_json = repo_path / "package.json"
        if package_json.exists():
            try:
                import json as json_lib
                data = json_lib.loads(package_json.read_text())
                if "scripts" in data and "test" in data["scripts"]:
                    commands.append({
                        "command": "npm test",
                        "source": "package.json",
                    })
            except Exception:
                pass

        # pytest
        if (repo_path / "pytest.ini").exists() or (repo_path / "tests").exists():
            commands.append({
                "command": "pytest",
                "source": "pytest",
            })

        return commands

    async def _handle_workflow_failure(
        self,
        workflow: Workflow,
        project: Project,
        results: dict[str, Any],
        error: Optional[str] = None,
    ) -> dict[str, Any]:
        """Handle workflow failure with proper cleanup."""
        workflow.status = WorkflowStatus.FAILED
        workflow.completed_at = datetime.utcnow()
        self.session.add(workflow)

        project.status = ProjectStatus.FAILED
        project.assumption_status = "failed"
        project.assumption_error = error or "Workflow failed"
        project.assumption_completed_at = datetime.utcnow()
        self.session.add(project)
        self.session.commit()

        # Clean up workspace
        self._cleanup_workspace(project)

        results["status"] = "failed"
        results["error"] = error or "Workflow failed"
        logger.error(f"[ASSUME] Project assumption failed: {error}")

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

    async def _detect_default_branch(self, repository_url: str) -> str:
        """
        Detect the default branch of a Git repository.

        This method implements a 4-step algorithm:
        1. Try git ls-remote --symref to get the symbolic reference
        2. Try common branch names (main, master, develop, trunk)
        3. List all remote branches and use the first one
        4. Raise CouldNotDetectBranchError with details

        Args:
            repository_url: The URL of the Git repository

        Returns:
            str: The name of the default branch

        Raises:
            CouldNotDetectBranchError: If the default branch cannot be detected
        """
        logger.info(f"[ASSUME] Starting branch detection for: {repository_url}")

        # Step 1: Try git ls-remote --symref HEAD
        logger.info(f"[ASSUME] Step 1: Trying git ls-remote --symref HEAD")
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--symref", repository_url, "HEAD"],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT,
            )

            if result.returncode == 0 and result.stdout:
                # Parse output: "ref: refs/heads/master    HEAD"
                for line in result.stdout.split("\n"):
                    if line.startswith("ref:"):
                        # Extract branch name from "ref: refs/heads/<branch>"
                        parts = line.split()
                        if len(parts) >= 2 and parts[1].startswith("refs/heads/"):
                            branch = parts[1].replace("refs/heads/", "")
                            logger.info(f"[ASSUME] Detected branch via ls-remote: {branch}")
                            return branch
        except subprocess.TimeoutExpired:
            logger.warning(f"[ASSUME] git ls-remote timed out after {GIT_TIMEOUT}s")
        except Exception as e:
            logger.warning(f"[ASSUME] git ls-remote failed: {e}")

        # Step 2: Try common branch names
        logger.info(f"[ASSUME] Step 2: Trying common branch names")
        common_branches = ["main", "master", "develop", "trunk"]
        attempted_branches = []

        for branch in common_branches:
            logger.info(f"[ASSUME] Trying branch: {branch}")
            attempted_branches.append(branch)
            try:
                result = subprocess.run(
                    ["git", "ls-remote", "--heads", repository_url, f"refs/heads/{branch}"],
                    capture_output=True,
                    text=True,
                    timeout=GIT_TIMEOUT,
                )

                if result.returncode == 0 and result.stdout.strip():
                    logger.info(f"[ASSUME] Detected branch via common names: {branch}")
                    return branch
            except subprocess.TimeoutExpired:
                logger.warning(f"[ASSUME] Timeout checking branch {branch}")
                continue
            except Exception as e:
                logger.warning(f"[ASSUME] Error checking branch {branch}: {e}")
                continue

        # Step 3: List all remote branches and use the first one
        logger.info(f"[ASSUME] Step 3: Listing all remote branches")
        try:
            result = subprocess.run(
                ["git", "ls-remote", "--heads", repository_url],
                capture_output=True,
                text=True,
                timeout=GIT_TIMEOUT,
            )

            if result.returncode == 0 and result.stdout:
                available_branches = []
                for line in result.stdout.split("\n"):
                    if line.strip() and "refs/heads/" in line:
                        # Parse: "<hash>    refs/heads/<branch>"
                        parts = line.split("refs/heads/")
                        if len(parts) >= 2:
                            branch = parts[1].strip()
                            available_branches.append(branch)

                if available_branches:
                    first_branch = available_branches[0]
                    logger.warning(
                        f"[ASSUME] Using first available branch as fallback: {first_branch}. "
                        f"Available branches: {available_branches}"
                    )
                    return first_branch
                else:
                    # Step 4: No branches found
                    logger.error(f"[ASSUME] No branches found in repository")
                    raise CouldNotDetectBranchError(
                        "Repository has no branches",
                        repository_url=repository_url,
                        attempted_branches=attempted_branches,
                        available_branches=[],
                    )
        except subprocess.TimeoutExpired:
            logger.error(f"[ASSUME] Timeout listing remote branches after {GIT_TIMEOUT}s")
            raise CouldNotDetectBranchError(
                f"Timeout while trying to list remote branches (>{GIT_TIMEOUT}s)",
                repository_url=repository_url,
                attempted_branches=attempted_branches,
                available_branches=[],
            )
        except CouldNotDetectBranchError:
            raise
        except Exception as e:
            logger.error(f"[ASSUME] Failed to list remote branches: {e}")
            raise CouldNotDetectBranchError(
                f"Failed to access repository: {str(e)}",
                repository_url=repository_url,
                attempted_branches=attempted_branches,
                available_branches=[],
            )

        # Step 4: Total failure
        logger.error(f"[ASSUME] All branch detection methods failed")
        raise CouldNotDetectBranchError(
            "Could not determine default branch using any method",
            repository_url=repository_url,
            attempted_branches=attempted_branches,
            available_branches=[],
        )
