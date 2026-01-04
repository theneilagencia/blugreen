from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.project import (
    Project,
    ProjectCreate,
    ProjectRead,
    ProjectStatus,
    ProjectUpdate,
)
from app.orchestrator import CentralOrchestrator

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectRead)
def create_project(
    project: ProjectCreate,
    session: Session = Depends(get_session),
) -> Project:
    db_project = Project.model_validate(project)
    session.add(db_project)
    session.commit()
    session.refresh(db_project)
    return db_project


@router.get("/", response_model=list[ProjectRead])
def list_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[ProjectStatus] = None,
    session: Session = Depends(get_session),
) -> list[Project]:
    query = select(Project)
    if status:
        query = query.where(Project.status == status)
    query = query.offset(skip).limit(limit)
    return list(session.exec(query).all())


@router.get("/{project_id}", response_model=ProjectRead)
def get_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    session: Session = Depends(get_session),
) -> Project:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    update_data = project_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(project, key, value)

    project.updated_at = datetime.utcnow()
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Delete a project and all associated workflows and tasks."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Delete associated workflows first (cascade)
    from app.models.workflow import Workflow
    workflows = session.query(Workflow).filter(Workflow.project_id == project_id).all()
    for workflow in workflows:
        session.delete(workflow)
    
    # Delete associated tasks (if any)
    from app.models.task import Task
    tasks = session.query(Task).filter(Task.project_id == project_id).all()
    for task in tasks:
        session.delete(task)
    
    # Now delete the project
    session.delete(project)
    session.commit()
    return {"message": "Project deleted"}


@router.post("/{project_id}/start")
async def start_project(
    project_id: int,
    requirements: str = "",
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orchestrator = CentralOrchestrator(session)
    result = await orchestrator.start_project(project, requirements)
    return result


@router.post("/{project_id}/execute-next")
async def execute_next_step(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orchestrator = CentralOrchestrator(session)
    result = await orchestrator.execute_next_step(project_id)
    return result


@router.post("/{project_id}/rollback")
async def rollback_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orchestrator = CentralOrchestrator(session)
    result = await orchestrator.rollback(project_id)
    return result


@router.get("/{project_id}/status")
def get_project_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orchestrator = CentralOrchestrator(session)
    return orchestrator.get_project_status(project_id)
