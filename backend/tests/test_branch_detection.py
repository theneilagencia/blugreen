"""Tests for branch detection in Project Assumption Service."""

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from sqlmodel import Session, create_engine
from sqlmodel.pool import StaticPool

from app.exceptions import CouldNotDetectBranchError
from app.models.project import Project
from app.services.project_assumption import ProjectAssumptionService


@pytest.fixture(name="session")
def session_fixture():
    """Create a test database session."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    from sqlmodel import SQLModel

    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


@pytest.fixture(name="service")
def service_fixture(session: Session):
    """Create a ProjectAssumptionService instance."""
    return ProjectAssumptionService(session)


class TestBranchDetection:
    """Test suite for _detect_default_branch method."""

    @pytest.mark.asyncio
    async def test_detect_branch_via_ls_remote_main(self, service: ProjectAssumptionService):
        """Test detecting 'main' branch via git ls-remote --symref."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ref: refs/heads/main\tHEAD\n1234567890abcdef\tHEAD\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            branch = await service._detect_default_branch("https://github.com/example/repo")

            assert branch == "main"
            mock_run.assert_called_once_with(
                ["git", "ls-remote", "--symref", "https://github.com/example/repo", "HEAD"],
                capture_output=True,
                text=True,
                timeout=30,
            )

    @pytest.mark.asyncio
    async def test_detect_branch_via_ls_remote_master(self, service: ProjectAssumptionService):
        """Test detecting 'master' branch via git ls-remote --symref."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ref: refs/heads/master\tHEAD\n1234567890abcdef\tHEAD\n"

        with patch("subprocess.run", return_value=mock_result) as mock_run:
            branch = await service._detect_default_branch("https://github.com/tiangolo/fastapi")

            assert branch == "master"
            mock_run.assert_called_once()

    @pytest.mark.asyncio
    async def test_detect_branch_via_common_names(self, service: ProjectAssumptionService):
        """Test detecting branch via common names when ls-remote fails."""
        # First call (ls-remote --symref) fails
        mock_symref_result = MagicMock()
        mock_symref_result.returncode = 1
        mock_symref_result.stdout = ""

        # Second call (ls-remote --heads for 'main') fails
        mock_main_result = MagicMock()
        mock_main_result.returncode = 0
        mock_main_result.stdout = ""

        # Third call (ls-remote --heads for 'master') succeeds
        mock_master_result = MagicMock()
        mock_master_result.returncode = 0
        mock_master_result.stdout = "1234567890abcdef\trefs/heads/master\n"

        with patch("subprocess.run", side_effect=[mock_symref_result, mock_main_result, mock_master_result]):
            branch = await service._detect_default_branch("https://github.com/example/repo")

            assert branch == "master"

    @pytest.mark.asyncio
    async def test_detect_branch_via_list_remotes(self, service: ProjectAssumptionService):
        """Test detecting branch by listing all remotes as fallback."""
        # First call (ls-remote --symref) fails
        mock_symref_result = MagicMock()
        mock_symref_result.returncode = 1
        mock_symref_result.stdout = ""

        # Calls for common branches all fail
        mock_empty_result = MagicMock()
        mock_empty_result.returncode = 0
        mock_empty_result.stdout = ""

        # Final call (ls-remote --heads) returns custom branches
        mock_list_result = MagicMock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = (
            "1234567890abcdef\trefs/heads/production\n"
            "abcdef1234567890\trefs/heads/staging\n"
        )

        with patch(
            "subprocess.run",
            side_effect=[
                mock_symref_result,
                mock_empty_result,  # main
                mock_empty_result,  # master
                mock_empty_result,  # develop
                mock_empty_result,  # trunk
                mock_list_result,  # list all
            ],
        ):
            branch = await service._detect_default_branch("https://github.com/example/custom-repo")

            assert branch == "production"

    @pytest.mark.asyncio
    async def test_detect_branch_inaccessible_repo(self, service: ProjectAssumptionService):
        """Test error handling for inaccessible repository."""
        # All subprocess calls fail
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            with pytest.raises(CouldNotDetectBranchError) as exc_info:
                await service._detect_default_branch("https://github.com/invalid/repo")

            error = exc_info.value
            assert error.repository_url == "https://github.com/invalid/repo"
            assert "main" in error.attempted_branches
            assert "master" in error.attempted_branches
            assert "develop" in error.attempted_branches
            assert "trunk" in error.attempted_branches

    @pytest.mark.asyncio
    async def test_detect_branch_invalid_url(self, service: ProjectAssumptionService):
        """Test error handling for invalid URL."""
        with pytest.raises(CouldNotDetectBranchError) as exc_info:
            await service._detect_default_branch("not-a-valid-url")

        error = exc_info.value
        assert "Invalid repository URL" in str(error)
        assert error.repository_url == "not-a-valid-url"

    @pytest.mark.asyncio
    async def test_detect_branch_timeout(self, service: ProjectAssumptionService):
        """Test error handling for timeout."""
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("git", 30)):
            with pytest.raises(CouldNotDetectBranchError) as exc_info:
                await service._detect_default_branch("https://github.com/slow/repo")

            error = exc_info.value
            assert "Timeout" in str(error)

    @pytest.mark.asyncio
    async def test_detect_branch_no_branches(self, service: ProjectAssumptionService):
        """Test error handling for repository with no branches."""
        # ls-remote --symref fails
        mock_symref_result = MagicMock()
        mock_symref_result.returncode = 1
        mock_symref_result.stdout = ""

        # All common branches fail
        mock_empty_result = MagicMock()
        mock_empty_result.returncode = 0
        mock_empty_result.stdout = ""

        # List all branches returns empty
        mock_list_result = MagicMock()
        mock_list_result.returncode = 0
        mock_list_result.stdout = ""

        with patch(
            "subprocess.run",
            side_effect=[
                mock_symref_result,
                mock_empty_result,  # main
                mock_empty_result,  # master
                mock_empty_result,  # develop
                mock_empty_result,  # trunk
                mock_list_result,  # list all
            ],
        ):
            with pytest.raises(CouldNotDetectBranchError) as exc_info:
                await service._detect_default_branch("https://github.com/empty/repo")

            error = exc_info.value
            assert "could not determine default branch" in str(error).lower()
            assert error.available_branches == []


class TestAssumeProjectWithBranchDetection:
    """Test suite for assume_project with automatic branch detection."""

    @pytest.mark.asyncio
    async def test_assume_project_with_explicit_branch(self, service: ProjectAssumptionService, session: Session):
        """Test assume_project with explicitly provided branch."""
        project = Project(name="Test Project", description="Test")
        session.add(project)
        session.commit()

        # Mock the entire flow
        with patch.object(service, "_step_fetch_repository") as mock_fetch, \
             patch.object(service, "_step_index_codebase") as mock_index, \
             patch.object(service, "_step_detect_stack") as mock_detect:

            mock_fetch.return_value = {"step": "fetch_repository", "success": True, "result": {}}
            mock_index.return_value = {"step": "index_codebase", "success": True, "result": {}}
            mock_detect.return_value = {"step": "detect_stack", "success": True, "result": {}}

            result = await service.assume_project(
                project,
                "https://github.com/example/repo",
                branch="custom-branch",
            )

            assert result["status"] == "success"
            assert result["branch"] == "custom-branch"
            # Verify that _detect_default_branch was NOT called
            mock_fetch.assert_called_once()
            args = mock_fetch.call_args[0]
            assert args[3] == "custom-branch"  # branch parameter

    @pytest.mark.asyncio
    async def test_assume_project_with_auto_detection(self, service: ProjectAssumptionService, session: Session):
        """Test assume_project with automatic branch detection."""
        project = Project(name="Test Project", description="Test")
        session.add(project)
        session.commit()

        # Mock branch detection
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "ref: refs/heads/main\tHEAD\n"

        with patch("subprocess.run", return_value=mock_result), \
             patch.object(service, "_step_fetch_repository") as mock_fetch, \
             patch.object(service, "_step_index_codebase") as mock_index, \
             patch.object(service, "_step_detect_stack") as mock_detect:

            mock_fetch.return_value = {"step": "fetch_repository", "success": True, "result": {}}
            mock_index.return_value = {"step": "index_codebase", "success": True, "result": {}}
            mock_detect.return_value = {"step": "detect_stack", "success": True, "result": {}}

            result = await service.assume_project(
                project,
                "https://github.com/example/repo",
                branch=None,  # No branch provided
            )

            assert result["status"] == "success"
            assert result["branch"] == "main"
            mock_fetch.assert_called_once()
            args = mock_fetch.call_args[0]
            assert args[3] == "main"  # detected branch

    @pytest.mark.asyncio
    async def test_assume_project_detection_failure(self, service: ProjectAssumptionService, session: Session):
        """Test assume_project when branch detection fails."""
        project = Project(name="Test Project", description="Test")
        session.add(project)
        session.commit()

        # Mock failed detection
        with patch.object(
            service,
            "_detect_default_branch",
            side_effect=CouldNotDetectBranchError(
                "Could not detect branch",
                repository_url="https://github.com/example/repo",
                attempted_branches=["main", "master"],
                available_branches=["feature-1", "feature-2"],
            ),
        ):
            result = await service.assume_project(
                project,
                "https://github.com/example/repo",
                branch=None,
            )

            assert result["status"] == "error"
            assert "Could not determine default branch" in result["message"]
            assert result["details"]["repository_url"] == "https://github.com/example/repo"
            assert "main" in result["details"]["attempted_branches"]
            assert "feature-1" in result["details"]["available_branches"]
