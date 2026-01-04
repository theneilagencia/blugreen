"""
Tests for Assume Flow (Project Assumption Service V2)

Tests cover:
- Valid repositories (main, master, custom branch)
- Invalid URLs
- Private repositories
- Empty repositories
- Git timeouts
- Retry after failure
- Duplicate execution blocking
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from pathlib import Path

from app.services.project_assumption_v2 import (
    ProjectAssumptionService,
    ValidationError,
    RepositoryAccessError,
)
from app.models.project import Project, ProjectStatus
from app.exceptions import CouldNotDetectBranchError


@pytest.fixture
def mock_session():
    """Create a mock database session."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.refresh = Mock()
    session.exec = Mock()
    return session


@pytest.fixture
def service(mock_session):
    """Create a ProjectAssumptionService instance with mocked session."""
    return ProjectAssumptionService(mock_session)


@pytest.fixture
def project():
    """Create a test project."""
    return Project(
        id=1,
        name="Test Project",
        description="Test project for assumption",
        status=ProjectStatus.DRAFT,
    )


class TestInputValidation:
    """Test input validation."""

    def test_validate_empty_url(self, service):
        """Test validation fails with empty URL."""
        with pytest.raises(ValidationError, match="Repository URL is required"):
            service._validate_input("", None)

    def test_validate_invalid_url_protocol(self, service):
        """Test validation fails with invalid URL protocol."""
        with pytest.raises(ValidationError, match="Invalid repository URL"):
            service._validate_input("ftp://example.com/repo.git", None)

    def test_validate_valid_https_url(self, service):
        """Test validation passes with valid HTTPS URL."""
        service._validate_input("https://github.com/user/repo.git", None)

    def test_validate_valid_ssh_url(self, service):
        """Test validation passes with valid SSH URL."""
        service._validate_input("git@github.com:user/repo.git", None)

    def test_validate_empty_branch(self, service):
        """Test validation fails with empty branch name."""
        with pytest.raises(ValidationError, match="Branch name cannot be empty"):
            service._validate_input("https://github.com/user/repo.git", "   ")


class TestBranchDetection:
    """Test branch detection."""

    @patch("subprocess.run")
    def test_detect_branch_via_symref(self, mock_run, service):
        """Test branch detection via git ls-remote --symref."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="ref: refs/heads/main\tHEAD\n",
        )

        branch = service._detect_default_branch("https://github.com/user/repo.git")
        assert branch == "main"

    @patch("subprocess.run")
    def test_detect_branch_via_common_names(self, mock_run, service):
        """Test branch detection via common branch names."""
        # First call (symref) fails
        # Second call (main) succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),
            Mock(returncode=0, stdout="abc123\trefs/heads/main\n"),
        ]

        branch = service._detect_default_branch("https://github.com/user/repo.git")
        assert branch == "main"

    @patch("subprocess.run")
    def test_detect_branch_master(self, mock_run, service):
        """Test branch detection with master branch."""
        # symref fails, main fails, master succeeds
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),
            Mock(returncode=0, stdout=""),
            Mock(returncode=0, stdout="abc123\trefs/heads/master\n"),
        ]

        branch = service._detect_default_branch("https://github.com/user/repo.git")
        assert branch == "master"

    @patch("subprocess.run")
    def test_detect_branch_timeout(self, mock_run, service):
        """Test branch detection handles timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        with pytest.raises(CouldNotDetectBranchError, match="Timeout"):
            service._detect_default_branch("https://github.com/user/repo.git")

    @patch("subprocess.run")
    def test_detect_branch_no_branches(self, mock_run, service):
        """Test branch detection fails when repository has no branches."""
        # All methods fail
        mock_run.side_effect = [
            Mock(returncode=1, stdout=""),  # symref
            Mock(returncode=0, stdout=""),  # main
            Mock(returncode=0, stdout=""),  # master
            Mock(returncode=0, stdout=""),  # develop
            Mock(returncode=0, stdout=""),  # trunk
            Mock(returncode=0, stdout=""),  # list all
        ]

        with pytest.raises(CouldNotDetectBranchError, match="Repository has no branches"):
            service._detect_default_branch("https://github.com/user/repo.git")


class TestRepositoryAccess:
    """Test repository access verification."""

    @patch("subprocess.run")
    def test_verify_access_success(self, mock_run, service):
        """Test repository access verification succeeds."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="abc123\trefs/heads/main\n",
        )

        service._verify_repository_access("https://github.com/user/repo.git", "main")

    @patch("subprocess.run")
    def test_verify_access_permission_denied(self, mock_run, service):
        """Test repository access fails with permission denied."""
        mock_run.return_value = Mock(
            returncode=128,
            stderr="Permission denied (publickey)",
        )

        with pytest.raises(RepositoryAccessError, match="Permission denied"):
            service._verify_repository_access("https://github.com/user/repo.git", "main")

    @patch("subprocess.run")
    def test_verify_access_branch_not_found(self, mock_run, service):
        """Test repository access fails when branch doesn't exist."""
        mock_run.return_value = Mock(
            returncode=0,
            stdout="",  # Empty means branch doesn't exist
        )

        with pytest.raises(RepositoryAccessError, match="Branch 'nonexistent' does not exist"):
            service._verify_repository_access("https://github.com/user/repo.git", "nonexistent")

    @patch("subprocess.run")
    def test_verify_access_timeout(self, mock_run, service):
        """Test repository access handles timeout."""
        import subprocess
        mock_run.side_effect = subprocess.TimeoutExpired("git", 30)

        with pytest.raises(RepositoryAccessError, match="timed out"):
            service._verify_repository_access("https://github.com/user/repo.git", "main")


class TestRepositoryValidation:
    """Test repository validation."""

    def test_is_repository_valid_success(self, service, tmp_path):
        """Test repository validation succeeds with valid repo."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()
        (repo_path / "README.md").write_text("# Test")

        assert service._is_repository_valid(repo_path) is True

    def test_is_repository_valid_no_git_dir(self, service, tmp_path):
        """Test repository validation fails without .git directory."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / "README.md").write_text("# Test")

        assert service._is_repository_valid(repo_path) is False

    def test_is_repository_valid_empty(self, service, tmp_path):
        """Test repository validation fails with empty repo."""
        repo_path = tmp_path / "repo"
        repo_path.mkdir()
        (repo_path / ".git").mkdir()

        assert service._is_repository_valid(repo_path) is False

    def test_is_repository_valid_not_exists(self, service, tmp_path):
        """Test repository validation fails when path doesn't exist."""
        repo_path = tmp_path / "nonexistent"

        assert service._is_repository_valid(repo_path) is False


class TestIdempotency:
    """Test idempotency."""

    @pytest.mark.asyncio
    async def test_assume_project_already_completed(self, service, project):
        """Test assume_project blocks duplicate execution."""
        project.assumption_status = "completed"

        result = await service.assume_project(
            project,
            "https://github.com/user/repo.git",
            "main",
        )

        assert result["status"] == "error"
        assert result["error_type"] == "already_assumed"
        assert "already assumed" in result["message"]

    @pytest.mark.asyncio
    async def test_assume_project_retry_after_failure(self, service, project):
        """Test assume_project allows retry after failure."""
        project.assumption_status = "failed"

        # This should NOT block execution
        # (actual execution will fail due to mocking, but that's OK)
        with patch.object(service, "_detect_default_branch") as mock_detect:
            mock_detect.side_effect = CouldNotDetectBranchError(
                "Test error",
                repository_url="https://github.com/user/repo.git",
            )

            result = await service.assume_project(
                project,
                "https://github.com/user/repo.git",
                "main",
            )

            # Should attempt execution (not blocked)
            assert result["status"] == "error"
            assert result["error_type"] == "branch_detection_failed"


class TestWorkspaceCleanup:
    """Test workspace cleanup."""

    def test_cleanup_workspace_success(self, service, project, tmp_path):
        """Test workspace cleanup succeeds."""
        with patch("app.services.project_assumption_v2.WORKSPACE_BASE", tmp_path):
            workspace = tmp_path / f"project_{project.id}"
            workspace.mkdir()
            (workspace / "test.txt").write_text("test")

            service._cleanup_workspace(project)

            assert not workspace.exists()

    def test_cleanup_workspace_not_exists(self, service, project, tmp_path):
        """Test workspace cleanup handles non-existent workspace."""
        with patch("app.services.project_assumption_v2.WORKSPACE_BASE", tmp_path):
            # Should not raise exception
            service._cleanup_workspace(project)


class TestErrorMessages:
    """Test error messages are descriptive."""

    @pytest.mark.asyncio
    async def test_error_message_invalid_url(self, service, project):
        """Test error message for invalid URL."""
        result = await service.assume_project(
            project,
            "ftp://example.com/repo.git",
            None,
        )

        assert result["status"] == "error"
        assert "Invalid repository URL" in result["message"]
        assert "https://" in result["message"]

    @pytest.mark.asyncio
    async def test_error_message_branch_not_found(self, service, project):
        """Test error message for branch not found."""
        with patch.object(service, "_detect_default_branch") as mock_detect:
            mock_detect.side_effect = CouldNotDetectBranchError(
                "Branch not found",
                repository_url="https://github.com/user/repo.git",
                available_branches=["main", "develop"],
                attempted_branches=["master"],
            )

            result = await service.assume_project(
                project,
                "https://github.com/user/repo.git",
                None,
            )

            assert result["status"] == "error"
            assert "Could not determine default branch" in result["message"]
            assert "available_branches" in result["details"]


class TestEndToEnd:
    """End-to-end tests."""

    @pytest.mark.asyncio
    @patch("subprocess.run")
    async def test_assume_project_success(self, mock_run, service, project, tmp_path):
        """Test full assume_project flow succeeds."""
        with patch("app.services.project_assumption_v2.WORKSPACE_BASE", tmp_path):
            # Mock git operations
            mock_run.side_effect = [
                # Branch detection (symref)
                Mock(returncode=0, stdout="ref: refs/heads/main\tHEAD\n"),
                # Repository access verification
                Mock(returncode=0, stdout="abc123\trefs/heads/main\n"),
                # Git clone
                Mock(returncode=0, stdout="Cloning into 'repo'...\n"),
            ]

            # Create fake repository
            repo_path = tmp_path / f"project_{project.id}" / "repo"
            repo_path.mkdir(parents=True)
            (repo_path / ".git").mkdir()
            (repo_path / "README.md").write_text("# Test")
            (repo_path / "package.json").write_text('{"name": "test"}')

            result = await service.assume_project(
                project,
                "https://github.com/user/repo.git",
                None,
            )

            assert result["status"] == "success"
            assert result["branch"] == "main"
            assert "elapsed_seconds" in result
            assert len(result["steps"]) == 3
