"""
API endpoints for project assumption (Phase 3).

Provides endpoints for:
- Assuming existing repositories
- Getting project context after assumption
- Running diagnostics on assumed projects
- Safe evolution of projects
"""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session, get_session_context
from app.models.project import Project, ProjectStatus
from app.services.diagnostics import DiagnosticsService
from app.services.project_assumption import ProjectAssumptionService
from app.services.safe_evolution import SafeEvolutionService

router = APIRouter(prefix="/assume", tags=["assumption"])

_assumption_tasks: dict[int, dict[str, Any]] = {}
_diagnostics_tasks: dict[int, dict[str, Any]] = {}
_evolution_tasks: dict[int, dict[str, Any]] = {}


class AssumeProjectRequest(BaseModel):
    name: str
    description: Optional[str] = None
    repository_url: str
    branch: str = "main"


class DiagnosticsRequest(BaseModel):
    pass


class EvolveProjectRequest(BaseModel):
    change_request: str


class RollbackRequest(BaseModel):
    pass


async def _run_assumption_task(project_id: int, repository_url: str, branch: str) -> None:
    """Background task to run project assumption."""
    with get_session_context() as session:
        project = session.get(Project, project_id)
        if not project:
            _assumption_tasks[project_id] = {
                "status": "failed",
                "error": "Project not found",
            }
            return

        service = ProjectAssumptionService(session)
        try:
            result = await service.assume_project(project, repository_url, branch)
            _assumption_tasks[project_id] = result
        except Exception as e:
            _assumption_tasks[project_id] = {
                "status": "failed",
                "error": str(e),
            }


async def _run_diagnostics_task(project_id: int) -> None:
    """Background task to run diagnostics."""
    with get_session_context() as session:
        project = session.get(Project, project_id)
        if not project:
            _diagnostics_tasks[project_id] = {
                "status": "failed",
                "error": "Project not found",
            }
            return

        service = DiagnosticsService(session)
        try:
            result = await service.run_diagnostics(project)
            _diagnostics_tasks[project_id] = result
        except Exception as e:
            _diagnostics_tasks[project_id] = {
                "status": "failed",
                "error": str(e),
            }


async def _run_evolution_task(project_id: int, change_request: str) -> None:
    """Background task to run safe evolution."""
    with get_session_context() as session:
        project = session.get(Project, project_id)
        if not project:
            _evolution_tasks[project_id] = {
                "status": "failed",
                "error": "Project not found",
            }
            return

        service = SafeEvolutionService(session)
        try:
            result = await service.evolve_project(project, change_request)
            _evolution_tasks[project_id] = result
        except Exception as e:
            _evolution_tasks[project_id] = {
                "status": "failed",
                "error": str(e),
            }


@router.post("/project")
async def assume_project(
    request: AssumeProjectRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Assume an existing repository.

    This endpoint clones the repository, analyzes its structure,
    and detects the technology stack. The process runs in the background.
    """
    project = Project(
        name=request.name,
        description=request.description,
        repository_url=request.repository_url,
        status=ProjectStatus.DRAFT,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    _assumption_tasks[project.id] = {"status": "in_progress", "steps": []}

    background_tasks.add_task(
        _run_assumption_task,
        project.id,
        request.repository_url,
        request.branch,
    )

    return {
        "status": "started",
        "project_id": project.id,
        "message": "Project assumption started in background",
        "monitor_url": f"/assume/project/{project.id}/status",
    }


@router.get("/project/{project_id}/status")
async def get_assumption_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the status of a project assumption task."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_status = _assumption_tasks.get(project_id, {"status": "unknown"})

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status.value,
        "assumption_status": task_status.get("status"),
        "steps": task_status.get("steps", []),
        "error": task_status.get("error"),
    }


@router.get("/project/{project_id}/context")
async def get_project_context(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the context of an assumed project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = ProjectAssumptionService(session)
    context = service.get_project_context(project)

    if not context:
        raise HTTPException(
            status_code=404,
            detail="Project context not found. Has the project been assumed?",
        )

    return {
        "project_id": project_id,
        "project_name": project.name,
        "context": context,
    }


@router.post("/project/{project_id}/diagnostics")
async def run_diagnostics(
    project_id: int,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Run diagnostics on an assumed project.

    This endpoint runs code quality, security, and UX/UI quality checks.
    The process runs in the background.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    _diagnostics_tasks[project_id] = {"status": "in_progress", "steps": []}

    background_tasks.add_task(_run_diagnostics_task, project_id)

    return {
        "status": "started",
        "project_id": project_id,
        "message": "Diagnostics started in background",
        "monitor_url": f"/assume/project/{project_id}/diagnostics/status",
    }


@router.get("/project/{project_id}/diagnostics/status")
async def get_diagnostics_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the status of a diagnostics task."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_status = _diagnostics_tasks.get(project_id, {"status": "unknown"})

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status.value,
        "diagnostics_status": task_status.get("status"),
        "summary": task_status.get("summary", {}),
        "steps": task_status.get("steps", []),
        "error": task_status.get("error"),
    }


@router.get("/project/{project_id}/diagnostics/latest")
async def get_latest_diagnostics(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the latest diagnostics results for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = DiagnosticsService(session)
    results = service.get_latest_diagnostics(project)

    if not results:
        raise HTTPException(
            status_code=404,
            detail="No diagnostics found for this project",
        )

    return {
        "project_id": project_id,
        "project_name": project.name,
        "diagnostics": results,
    }


@router.post("/project/{project_id}/evolve")
async def evolve_project(
    project_id: int,
    request: EvolveProjectRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Safely evolve a project based on a change request.

    This endpoint creates a baseline, plans changes, implements them,
    and deploys with automatic rollback on failure.
    The process runs in the background.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    _evolution_tasks[project_id] = {"status": "in_progress", "steps": []}

    background_tasks.add_task(
        _run_evolution_task,
        project_id,
        request.change_request,
    )

    return {
        "status": "started",
        "project_id": project_id,
        "message": "Safe evolution started in background",
        "monitor_url": f"/assume/project/{project_id}/evolve/status",
    }


@router.get("/project/{project_id}/evolve/status")
async def get_evolution_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the status of a safe evolution task."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    task_status = _evolution_tasks.get(project_id, {"status": "unknown"})

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status.value,
        "evolution_status": task_status.get("status"),
        "steps": task_status.get("steps", []),
        "error": task_status.get("error"),
        "rollback": task_status.get("rollback"),
    }


@router.get("/project/{project_id}/evolve/history")
async def get_evolution_history(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """Get the evolution history for a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = SafeEvolutionService(session)
    history = service.get_evolution_history(project)

    return {
        "project_id": project_id,
        "project_name": project.name,
        "history": history,
    }


@router.post("/project/{project_id}/rollback")
async def rollback_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    """
    Manually rollback a project to its last baseline.

    This endpoint reverts the project to its last known good state.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    service = SafeEvolutionService(session)
    result = await service.rollback_to_baseline(project)

    if result.get("status") == "failed":
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "Rollback failed"),
        )

    return {
        "status": "success",
        "project_id": project_id,
        "project_name": project.name,
        "rollback_result": result,
    }
