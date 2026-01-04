"""
Project deletion service with business rules and validation.

This module implements the governed DELETE behavior, ensuring that
projects cannot be deleted while they have active processes.
"""

from typing import Tuple, Optional
from sqlmodel import Session, select
from app.models.project import Project, ProjectStatus
from app.models.workflow import Workflow, WorkflowStatus
from app.models.product import Product, ProductStatus
from app.models.task import Task, TaskStatus


class DeletionBlockReason:
    """Reason codes for deletion blocking."""
    ACTIVE_WORKFLOW = "active_workflow"
    ACTIVE_PRODUCT = "active_product"
    ACTIVE_TASK = "active_task"
    PROJECT_RUNNING = "project_running"


def can_delete_project(project_id: int, session: Session) -> Tuple[bool, Optional[str]]:
    """
    Check if a project can be safely deleted.
    
    Args:
        project_id: ID of the project to check
        session: Database session
        
    Returns:
        Tuple of (can_delete: bool, reason_code: Optional[str])
        
    Business Rules:
        - Projects with RUNNING status cannot be deleted
        - Projects with active workflows cannot be deleted
        - Projects with active products cannot be deleted
        - Projects with pending/running tasks cannot be deleted
    """
    
    # Check if project exists
    project = session.get(Project, project_id)
    if not project:
        return True, None  # Non-existent projects can be "deleted" (404 will be returned)
    
    # Rule 1: Check project status
    if project.status == ProjectStatus.RUNNING:
        return False, DeletionBlockReason.PROJECT_RUNNING
    
    # Rule 2: Check for active workflows
    active_workflows = session.exec(
        select(Workflow)
        .where(Workflow.project_id == project_id)
        .where(Workflow.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PENDING]))
    ).all()
    
    if active_workflows:
        return False, DeletionBlockReason.ACTIVE_WORKFLOW
    
    # Rule 3: Check for active products
    active_products = session.exec(
        select(Product)
        .where(Product.project_id == project_id)
        .where(Product.status.in_([ProductStatus.RUNNING, ProductStatus.PENDING]))
    ).all()
    
    if active_products:
        return False, DeletionBlockReason.ACTIVE_PRODUCT
    
    # Rule 4: Check for active tasks
    active_tasks = session.exec(
        select(Task)
        .where(Task.project_id == project_id)
        .where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]))
    ).all()
    
    if active_tasks:
        return False, DeletionBlockReason.ACTIVE_TASK
    
    # All checks passed - project can be deleted
    return True, None


def get_deletion_block_message(reason_code: str) -> dict:
    """
    Get user-friendly message for deletion block reason.
    
    Args:
        reason_code: Reason code from DeletionBlockReason
        
    Returns:
        Dictionary with code and user-friendly message
    """
    messages = {
        DeletionBlockReason.ACTIVE_WORKFLOW: {
            "code": "PROJECT_ACTIVE",
            "reason": reason_code,
            "message": "Este projeto possui workflows em execução. Finalize ou pause as execuções ativas antes de removê-lo.",
            "message_en": "This project has active workflows. Please finish or pause active executions before removing it."
        },
        DeletionBlockReason.ACTIVE_PRODUCT: {
            "code": "PROJECT_ACTIVE",
            "reason": reason_code,
            "message": "Este projeto possui produtos em execução. Finalize ou pause as execuções ativas antes de removê-lo.",
            "message_en": "This project has active products. Please finish or pause active executions before removing it."
        },
        DeletionBlockReason.ACTIVE_TASK: {
            "code": "PROJECT_ACTIVE",
            "reason": reason_code,
            "message": "Este projeto possui tarefas em execução. Finalize ou pause as execuções ativas antes de removê-lo.",
            "message_en": "This project has active tasks. Please finish or pause active executions before removing it."
        },
        DeletionBlockReason.PROJECT_RUNNING: {
            "code": "PROJECT_ACTIVE",
            "reason": reason_code,
            "message": "Este projeto está em execução no momento. Para removê-lo com segurança, finalize ou pause as execuções ativas. Nenhum dado foi apagado.",
            "message_en": "This project is currently running. To safely remove it, please finish or pause active executions. No data has been deleted."
        }
    }
    
    return messages.get(reason_code, {
        "code": "PROJECT_ACTIVE",
        "reason": "unknown",
        "message": "Este projeto não pode ser removido no momento. Finalize as execuções ativas antes de tentar novamente.",
        "message_en": "This project cannot be removed at this time. Please finish active executions before trying again."
    })


async def close_project(project_id: int, session: Session) -> dict:
    """
    Close a project by stopping all active processes.
    
    Args:
        project_id: ID of the project to close
        session: Database session
        
    Returns:
        Dictionary with operation result
        
    Actions:
        - Stop all running workflows
        - Stop all running products
        - Cancel all pending/running tasks
        - Mark project as INACTIVE
    """
    
    project = session.get(Project, project_id)
    if not project:
        return {"success": False, "error": "Project not found"}
    
    # Stop active workflows
    active_workflows = session.exec(
        select(Workflow)
        .where(Workflow.project_id == project_id)
        .where(Workflow.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PENDING]))
    ).all()
    
    for workflow in active_workflows:
        workflow.status = WorkflowStatus.CANCELLED
        session.add(workflow)
    
    # Stop active products
    active_products = session.exec(
        select(Product)
        .where(Product.project_id == project_id)
        .where(Product.status.in_([ProductStatus.RUNNING, ProductStatus.PENDING]))
    ).all()
    
    for product in active_products:
        product.status = ProductStatus.CANCELLED
        session.add(product)
    
    # Cancel active tasks
    active_tasks = session.exec(
        select(Task)
        .where(Task.project_id == project_id)
        .where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]))
    ).all()
    
    for task in active_tasks:
        task.status = TaskStatus.CANCELLED
        session.add(task)
    
    # Mark project as inactive
    project.status = ProjectStatus.DRAFT  # or INACTIVE if that status exists
    session.add(project)
    
    session.commit()
    
    return {
        "success": True,
        "workflows_stopped": len(active_workflows),
        "products_stopped": len(active_products),
        "tasks_cancelled": len(active_tasks)
    }
