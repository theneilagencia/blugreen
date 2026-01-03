"""
Test suite for Task title validation.

Ensures that Tasks are never created with title=None,
violating the NOT NULL constraint in the database.
"""

import pytest
from app.models.task import Task, TaskType, TaskStatus


def test_task_with_explicit_title():
    """Test that a Task with explicit title works correctly."""
    task = Task(
        title="Test Task",
        description="Test description",
        task_type=TaskType.PLANNING,
        project_id=1,
    )
    assert task.title == "Test Task"
    assert task.title is not None


def test_task_without_title_gets_fallback():
    """Test that a Task without title gets automatic fallback."""
    task = Task(
        title=None,  # Explicitly passing None
        description="Test description",
        task_type=TaskType.PLANNING,
        project_id=1,
    )
    assert task.title is not None
    assert task.title == "Untitled Planning"


def test_task_with_empty_title_gets_fallback():
    """Test that a Task with empty string title gets fallback."""
    task = Task(
        title="",  # Empty string
        description="Test description",
        task_type=TaskType.BACKEND,
        project_id=1,
    )
    assert task.title is not None
    assert task.title == "Untitled Backend"


def test_task_with_whitespace_title_gets_fallback():
    """Test that a Task with whitespace-only title gets fallback."""
    task = Task(
        title="   ",  # Whitespace only
        description="Test description",
        task_type=TaskType.FRONTEND,
        project_id=1,
    )
    assert task.title is not None
    assert task.title == "Untitled Frontend"


def test_task_title_fallback_for_different_types():
    """Test that fallback works correctly for different task types."""
    test_cases = [
        (TaskType.PLANNING, "Untitled Planning"),
        (TaskType.BACKEND, "Untitled Backend"),
        (TaskType.FRONTEND, "Untitled Frontend"),
        (TaskType.TESTING, "Untitled Testing"),
        (TaskType.DEPLOYMENT, "Untitled Deployment"),
        (TaskType.UX_REVIEW, "Untitled Ux Review"),
        (TaskType.UI_REFINEMENT, "Untitled Ui Refinement"),
        (TaskType.INFRA, "Untitled Infra"),
    ]
    
    for task_type, expected_title in test_cases:
        task = Task(
            title=None,
            description="Test",
            task_type=task_type,
            project_id=1,
        )
        assert task.title == expected_title, f"Failed for {task_type}"


def test_task_title_strips_whitespace():
    """Test that title whitespace is stripped."""
    task = Task(
        title="  Test Task  ",
        description="Test description",
        task_type=TaskType.PLANNING,
        project_id=1,
    )
    assert task.title == "Test Task"


def test_task_with_all_fields():
    """Test that a complete Task creation works."""
    task = Task(
        title="Complete Task",
        description="Full description",
        task_type=TaskType.TESTING,
        status=TaskStatus.IN_PROGRESS,
        project_id=1,
        assigned_agent="test_agent",
        error_message=None,
    )
    assert task.title == "Complete Task"
    assert task.description == "Full description"
    assert task.task_type == TaskType.TESTING
    assert task.status == TaskStatus.IN_PROGRESS
    assert task.project_id == 1
    assert task.assigned_agent == "test_agent"
