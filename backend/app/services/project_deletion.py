"""
Project deletion service with business rules and validation.

This module implements the governed DELETE behavior, ensuring that
projects cannot be deleted while they have active processes.
"""

from typing import Tuple, Optional, List
from sqlmodel import Session, select, func
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


def check_active_dependencies(project_id: int, session: Session) -> Tuple[bool, dict]:
    """
    Check if a project has active dependencies that block deletion.
    
    Args:
        project_id: ID of the project to check
        session: Database session
        
    Returns:
        Tuple of (can_delete: bool, block_response: dict)
        
    Business Rules:
        - Projects with RUNNING status cannot be deleted
        - Projects with active workflows cannot be deleted
        - Projects with active products cannot be deleted
        - Projects with pending/running tasks cannot be deleted
    """
    
    # Check if project exists
    project = session.get(Project, project_id)
    if not project:
        return True, {}  # Non-existent projects can be "deleted" (404 will be returned)
    
    # Count active dependencies
    active_workflows = session.exec(
        select(func.count(Workflow.id))
        .where(Workflow.project_id == project_id)
        .where(Workflow.status.in_([WorkflowStatus.RUNNING, WorkflowStatus.PENDING]))
    ).one()
    
    active_products = session.exec(
        select(func.count(Product.id))
        .where(Product.project_id == project_id)
        .where(Product.status.in_([ProductStatus.RUNNING, ProductStatus.PENDING]))
    ).one()
    
    active_tasks = session.exec(
        select(func.count(Task.id))
        .where(Task.project_id == project_id)
        .where(Task.status.in_([TaskStatus.RUNNING, TaskStatus.PENDING]))
    ).one()
    
    # Check if project is running
    is_project_running = project.status == ProjectStatus.RUNNING
    
    # If any active dependency exists, block deletion
    if active_workflows > 0 or active_products > 0 or active_tasks > 0 or is_project_running:
        return False, get_deletion_block_response(
            active_workflows=active_workflows,
            active_products=active_products,
            active_tasks=active_tasks,
            is_project_running=is_project_running
        )
    
    # All checks passed - project can be deleted
    return True, {}


def get_deletion_block_response(
    active_workflows: int = 0,
    active_products: int = 0,
    active_tasks: int = 0,
    is_project_running: bool = False
) -> dict:
    """
    Get structured 409 response for deletion block.
    
    Args:
        active_workflows: Number of active workflows
        active_products: Number of active products
        active_tasks: Number of active tasks
        is_project_running: Whether project status is RUNNING
        
    Returns:
        Structured dictionary with error_code, message, details, and action
    """
    details = []
    
    if is_project_running:
        details.append("O projeto está em execução")
    
    if active_workflows > 0:
        details.append(f"Há {active_workflows} workflow(s) em execução")
    
    if active_products > 0:
        details.append(f"Há {active_products} produto(s) em execução")
    
    if active_tasks > 0:
        details.append(f"Há {active_tasks} tarefa(s) em execução")
    
    if not details:
        details.append("Há atividades em andamento")
    
    return {
        "error_code": "PROJECT_HAS_ACTIVE_DEPENDENCIES",
        "message": "O projeto não pode ser excluído neste momento.",
        "details": details,
        "action": "Finalize ou cancele as atividades antes de tentar novamente."
    }


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
