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
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
def update_project(
    project_id: int,
    project_update: ProjectUpdate,
    session: Session = Depends(get_session),
) -> Project:
    project = session.query(Project).filter(Project.id == project_id).first()
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
    force: bool = False,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """
    Delete a project. Related records are automatically deleted via CASCADE.
    
    Business Rules:
    - Projects with active workflows/products/tasks cannot be deleted
    - Use POST /projects/:id/close to stop active processes first
    - Admin can use ?force=true to force deletion (cancels active processes)
    """
    from app.services.project_deletion import check_active_dependencies
    
    # Step 1: Check if project exists
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(
            status_code=404,
            detail={"error_code": "PROJECT_NOT_FOUND", "message": "Project not found"}
        )

    # Step 2: Check for active dependencies (PRE-VALIDATION)
    can_delete, block_response = check_active_dependencies(project_id, session)
    
    if not can_delete and not force:
        # Return 409 Conflict with structured response
        raise HTTPException(
            status_code=409,
            detail=block_response
        )
    
    if not can_delete and force:
        # Force delete: stop all active processes first
        from app.services.project_deletion import close_project
        await close_project(project_id, session)

    # Step 3: Delete the project - database CASCADE will handle related records
    session.delete(project)
    session.commit()
    
    # Step 4: Return success response
    return {"status": "deleted", "project_id": project_id}


@router.post("/{project_id}/close")
async def close_project_endpoint(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """
    Close a project by stopping all active processes.
    
    This endpoint prepares the project for safe deletion by:
    - Stopping all running workflows
    - Stopping all running products
    - Cancelling all pending/running tasks
    - Marking the project as inactive
    
    After closing, the project can be safely deleted.
    """
    from app.services.project_deletion import close_project
    
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    result = await close_project(project_id, session)
    
    if not result["success"]:
        raise HTTPException(status_code=500, detail=result["error"])
    
    return {
        "message": "Project closed successfully",
        "workflows_stopped": result["workflows_stopped"],
        "products_stopped": result["products_stopped"],
        "tasks_cancelled": result["tasks_cancelled"]
    }


@router.post("/{project_id}/start")
async def start_project(
    project_id: int,
    requirements: str = "",
    session: Session = Depends(get_session),
) -> dict:
    project = session.query(Project).filter(Project.id == project_id).first()
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
    project = session.query(Project).filter(Project.id == project_id).first()
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
    project = session.query(Project).filter(Project.id == project_id).first()
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
    project = session.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    orchestrator = CentralOrchestrator(session)
    return orchestrator.get_project_status(project_id)
