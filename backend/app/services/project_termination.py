"""
Project termination service.

Implements the governed lifecycle: ACTIVE → TERMINATING → TERMINATED

This module ensures that projects are gracefully shut down before deletion,
preventing IntegrityError, 500 errors, and inconsistent state.
"""

import logging
from sqlmodel import Session, select
from app.models.project import Project, ProjectStatus
from app.models.workflow import Workflow, WorkflowStatus
from app.models.product import Product, ProductStatus
from app.models.task import Task, TaskStatus

logger = logging.getLogger(__name__)


class TerminationError(Exception):
    """Base exception for termination errors."""
    pass


class ProjectNotActiveError(TerminationError):
    """Raised when trying to terminate a non-ACTIVE project."""
    def __init__(self, current_status: ProjectStatus):
        self.current_status = current_status
        super().__init__(f"Project is not ACTIVE (current: {current_status})")


async def terminate_project(project_id: int, session: Session) -> dict:
    """
    Terminate a project gracefully.
    
    Lifecycle: ACTIVE → TERMINATING → TERMINATED
    
    Args:
        project_id: ID of the project to terminate
        session: Database session
        
    Returns:
        Dictionary with termination result
        
    Raises:
        ProjectNotActiveError: If project is not in ACTIVE state
        
    Actions:
        1. Verify project is ACTIVE
        2. Set status to TERMINATING
        3. Cancel all running workflows
        4. Cancel all running products
        5. Cancel all running tasks
        6. Set status to TERMINATED
        7. Return summary
        
    Business Rules:
        - Only ACTIVE projects can be terminated
        - Termination is idempotent (TERMINATED projects return success)
        - Never raises exceptions for business logic
        - Never returns 500 for expected scenarios
    """
    
    # Step 1: Get project
    project = session.get(Project, project_id)
    if not project:
        return {
            "success": False,
            "error_code": "PROJECT_NOT_FOUND",
            "message": "Project not found"
        }
    
    # Step 2: Check if project is already TERMINATED (idempotent)
    if project.status == ProjectStatus.TERMINATED:
        logger.info(f"[TERMINATE] Project {project_id} already TERMINATED")
        return {
            "success": True,
            "already_terminated": True,
            "message": "Project was already terminated"
        }
    
    # Step 3: Check if project is ACTIVE
    if project.status != ProjectStatus.ACTIVE:
        logger.warning(f"[TERMINATE] Project {project_id} is not ACTIVE (current: {project.status})")
        return {
            "success": False,
            "error_code": "PROJECT_NOT_ACTIVE",
            "message": f"Project is not active (current status: {project.status.value})",
            "current_status": project.status.value
        }
    
    logger.info(f"[TERMINATE] Starting termination of project {project_id}")
    
    # Step 4: Set status to TERMINATING
    project.status = ProjectStatus.TERMINATING
    session.add(project)
    session.commit()
    
    # Step 5: Cancel all running workflows
    running_workflows = session.exec(
        select(Workflow)
        .where(Workflow.project_id == project_id)
        .where(Workflow.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PENDING]))
    ).all()
    
    for workflow in running_workflows:
        workflow.status = WorkflowStatus.CANCELLED
        session.add(workflow)
    
    workflows_cancelled = len(running_workflows)
    logger.info(f"[TERMINATE] Cancelled {workflows_cancelled} workflows")
    
    # Step 6: Cancel all running products
    running_products = session.exec(
        select(Product)
        .where(Product.project_id == project_id)
        .where(Product.status.in_([ProductStatus.RUNNING, ProductStatus.PENDING]))
    ).all()
    
    for product in running_products:
        product.status = ProductStatus.CANCELLED
        session.add(product)
    
    products_cancelled = len(running_products)
    logger.info(f"[TERMINATE] Cancelled {products_cancelled} products")
    
    # Step 7: Cancel all running tasks
    running_tasks = session.exec(
        select(Task)
        .where(Task.project_id == project_id)
        .where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]))
    ).all()
    
    for task in running_tasks:
        task.status = TaskStatus.CANCELLED
        session.add(task)
    
    tasks_cancelled = len(running_tasks)
    logger.info(f"[TERMINATE] Cancelled {tasks_cancelled} tasks")
    
    # Step 8: Set status to TERMINATED
    project.status = ProjectStatus.TERMINATED
    session.add(project)
    session.commit()
    
    logger.info(f"[TERMINATE] Project {project_id} successfully TERMINATED")
    
    # Step 9: Return summary
    return {
        "success": True,
        "project_id": project_id,
        "workflows_cancelled": workflows_cancelled,
        "products_cancelled": products_cancelled,
        "tasks_cancelled": tasks_cancelled,
        "message": "Project terminated successfully"
    }


def can_delete_project(project: Project) -> tuple[bool, dict]:
    """
    Check if a project can be deleted.
    
    Args:
        project: Project instance
        
    Returns:
        Tuple of (can_delete: bool, error_response: dict)
        
    Business Rules:
        - Only TERMINATED projects can be deleted
        - All other states return 409 with clear message
    """
    
    if project.status != ProjectStatus.TERMINATED:
        return False, {
            "error_code": "PROJECT_NOT_TERMINATED",
            "message": "O projeto precisa ser encerrado antes de ser excluído.",
            "current_status": project.status.value,
            "action": "Use POST /projects/{id}/terminate para encerrar o projeto primeiro."
        }
    
    return True, {}
