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
def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
):
    """
    Delete a project - NO-THROW ZONE.
    
    ABSOLUTE RULES:
    - NEVER throws exception
    - ALWAYS returns JSON
    - ALWAYS includes CORS headers
    - NEVER returns 500 without body
    
    This is a critical operation. Robustness > Elegance.
    """
    from fastapi.responses import JSONResponse
    import logging
    
    logger = logging.getLogger(__name__)
    
    try:
        # Step 1: Get project
        project = session.get(Project, project_id)
        
        if not project:
            return JSONResponse(
                status_code=404,
                content={
                    "error_code": "PROJECT_NOT_FOUND",
                    "message": "Projeto não encontrado."
                }
            )
        
        # Step 2: Check if project can be deleted
        # Allow deletion of: DRAFT, TERMINATED, FAILED, ROLLED_BACK
        deletable_statuses = [
            ProjectStatus.DRAFT,
            ProjectStatus.TERMINATED,
            ProjectStatus.FAILED,
            ProjectStatus.ROLLED_BACK
        ]
        if project.status not in deletable_statuses:
            return JSONResponse(
                status_code=409,
                content={
                    "error_code": "PROJECT_ACTIVE",
                    "message": "Finalize o projeto antes de excluir."
                }
            )
        
        # Step 3: Delete project
        session.delete(project)
        
        # Step 4: Commit with safety net
        try:
            session.commit()
        except Exception:
            session.rollback()
            return JSONResponse(
                status_code=409,
                content={
                    "error_code": "PROJECT_DELETE_CONSTRAINT",
                    "message": "O projeto ainda possui vínculos internos."
                }
            )
        
        # Step 5: Success
        return JSONResponse(
            status_code=200,
            content={"status": "deleted"}
        )
    
    except Exception as e:
        # ULTIMATE SAFETY NET: NO EXCEPTION ESCAPES
        logger.exception("DELETE PROJECT HARD FAILURE")
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "PROJECT_DELETE_INTERNAL_ERROR",
                "message": "Erro interno ao excluir projeto."
            }
        )


@router.post("/{project_id}/terminate")
async def terminate_project_endpoint(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """
    Terminate a project gracefully.
    
    Lifecycle: ACTIVE → TERMINATING → TERMINATED
    
    This endpoint:
    1. Verifies project is ACTIVE
    2. Sets status to TERMINATING
    3. Cancels all running workflows, products, and tasks
    4. Sets status to TERMINATED
    5. Returns summary
    
    Business Rules:
    - Only ACTIVE projects can be terminated
    - TERMINATED projects return success (idempotent)
    - Never returns 500 for business logic
    - Projects must be TERMINATED before deletion
    
    Returns:
        200: Project terminated successfully
        404: Project not found
        409: Project is not ACTIVE
    """
    from app.services.project_termination import terminate_project
    
    result = await terminate_project(project_id, session)
    
    if not result["success"]:
        error_code = result.get("error_code")
        
        if error_code == "PROJECT_NOT_FOUND":
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "PROJECT_NOT_FOUND",
                    "message": "Project not found"
                }
            )
        
        if error_code == "PROJECT_NOT_ACTIVE":
            raise HTTPException(
                status_code=409,
                detail={
                    "error_code": "PROJECT_NOT_ACTIVE",
                    "message": result["message"],
                    "current_status": result["current_status"]
                }
            )
    
    return result


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
