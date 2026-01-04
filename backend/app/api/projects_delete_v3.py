"""
DELETE endpoint blindado contra 500.

REGRA ABSOLUTA:
- NENHUMA exceção de regra de negócio pode gerar erro 500
- DELETE nunca pode lançar exception não tratada
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_session
from app.models.project import Project, ProjectStatus
from app.services.project_termination import can_delete_project

import logging

logger = logging.getLogger(__name__)

router = APIRouter()


@router.delete("/{project_id}")
async def delete_project(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """
    Delete a project (TERMINATED projects only).
    
    Lifecycle: ACTIVE → TERMINATING → TERMINATED → DELETED
    
    Business Rules:
    - Only TERMINATED projects can be deleted
    - All other states return 409
    - Never returns 500 for business logic
    - Database CASCADE handles related records
    
    Returns:
        200: Project deleted successfully
        404: Project not found
        409: Project not TERMINATED
        409: Delete blocked by constraint (safety net)
    
    Safety Net:
    - If IntegrityError occurs despite checks, returns 409 (not 500)
    - This prevents ANY database constraint from causing 500
    """
    
    logger.info(f"[DELETE] Attempting to delete project {project_id}")
    
    # Step 1: Check if project exists
    project = session.get(Project, project_id)
    if not project:
        logger.warning(f"[DELETE] Project {project_id} not found")
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "PROJECT_NOT_FOUND",
                "message": "Project not found"
            }
        )
    
    # Step 2: Check if project is TERMINATED
    can_delete, error_response = can_delete_project(project)
    
    if not can_delete:
        logger.warning(f"[DELETE] Project {project_id} is not TERMINATED (current: {project.status})")
        raise HTTPException(
            status_code=409,
            detail=error_response
        )
    
    logger.info(f"[DELETE] Project {project_id} is TERMINATED, proceeding with deletion")
    
    # Step 3: Delete the project with safety net
    try:
        session.delete(project)
        session.commit()
        logger.info(f"[DELETE] Project {project_id} deleted successfully")
        
        return {
            "status": "deleted",
            "project_id": project_id
        }
    
    except IntegrityError as e:
        # SAFETY NET: If IntegrityError occurs despite checks, rollback and return 409
        logger.error(f"[DELETE] IntegrityError for project {project_id}: {str(e)}")
        session.rollback()
        
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "PROJECT_DELETE_BLOCKED_BY_CONSTRAINT",
                "message": "Este projeto ainda possui vínculos internos que impedem a exclusão.",
                "action": "Finalize ou encerre todas as atividades antes de excluir.",
                "technical_detail": str(e) if logger.level == logging.DEBUG else None
            }
        )
    
    except Exception as e:
        # ULTIMATE SAFETY NET: Catch any other exception
        logger.error(f"[DELETE] Unexpected error for project {project_id}: {str(e)}", exc_info=True)
        session.rollback()
        
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_ERROR",
                "message": "Ocorreu um erro inesperado. Tente novamente em instantes.",
                "technical_detail": str(e) if logger.level == logging.DEBUG else None
            }
        )
