"""
Product Creation API - Endpoints for creating products from zero.

This API provides endpoints to:
- Create a new product from requirements
- Get product creation status
- Trigger deployment
- Trigger rollback
"""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlmodel import Session

from app.database import get_session
from app.models.project import Project, ProjectStatus
from app.services.deployment import get_deployment_service
from app.services.product_creation import ProductCreationService

router = APIRouter(prefix="/product", tags=["product"])


class ProductCreateRequest(BaseModel):
    """Request model for creating a new product."""

    name: str
    description: str
    requirements: str


class DeployRequest(BaseModel):
    """Request model for deploying a product."""

    docker_image: str
    environment_variables: dict[str, str] | None = None


_creation_tasks: dict[int, dict] = {}


@router.post("/create")
async def create_product(
    request: ProductCreateRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
) -> dict:
    """
    Create a new product from requirements.

    This endpoint initiates the complete product creation workflow:
    1. Interpret requirement
    2. Create technical plan
    3. Validate plan
    4. Generate code
    5. Create tests
    6. Run tests
    7. Build
    8. Deploy
    9. Monitor

    The workflow runs in the background and can be monitored via /product/{project_id}/status
    """
    project = Project(
        name=request.name,
        description=request.description,
        status=ProjectStatus.DRAFT,
    )
    session.add(project)
    session.commit()
    session.refresh(project)

    _creation_tasks[project.id] = {
        "status": "started",
        "project_id": project.id,
        "message": "Product creation started",
    }

    background_tasks.add_task(
        _run_product_creation,
        project.id,
        request.requirements,
    )

    return {
        "status": "started",
        "project_id": project.id,
        "message": f"Product creation started for '{request.name}'",
        "monitor_url": f"/product/{project.id}/status",
    }


async def _run_product_creation(project_id: int, requirements: str) -> None:
    """Background task to run the product creation workflow."""
    from app.database import get_session_context

    with get_session_context() as session:
        project = session.get(Project, project_id)
        if not project:
            _creation_tasks[project_id] = {
                "status": "error",
                "error": "Project not found",
            }
            return

        service = ProductCreationService(session)
        result = await service.create_product(project, requirements)
        _creation_tasks[project_id] = result


@router.get("/{project_id}/status")
def get_product_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Get the status of a product creation workflow."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    creation_status = _creation_tasks.get(project_id, {})

    return {
        "project_id": project_id,
        "project_name": project.name,
        "project_status": project.status.value,
        "creation_status": creation_status.get("status", "unknown"),
        "steps": creation_status.get("steps", []),
        "error": creation_status.get("error"),
    }


@router.post("/{project_id}/deploy")
async def deploy_product(
    project_id: int,
    request: DeployRequest,
    session: Session = Depends(get_session),
) -> dict:
    """
    Deploy a product to production via Coolify.

    This endpoint triggers the deployment workflow:
    1. Build Docker
    2. Publish to Coolify
    3. Healthcheck
    4. Rollback if failed
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project.status not in [ProjectStatus.TESTING, ProjectStatus.DEPLOYED, ProjectStatus.FAILED]:
        raise HTTPException(
            status_code=400,
            detail=f"Project must be in testing, deployed, or failed status to deploy. Current: {project.status.value}",
        )

    deployment_service = get_deployment_service()
    result = await deployment_service.deploy(
        project_name=project.name,
        docker_image=request.docker_image,
        environment_variables=request.environment_variables,
    )

    if result.get("status") == "success":
        project.status = ProjectStatus.DEPLOYED
        session.add(project)
        session.commit()

    return result


@router.post("/{project_id}/rollback")
async def rollback_product(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """
    Rollback a product deployment.

    This endpoint triggers the rollback workflow to restore
    the previous deployment version.
    """
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deployment_service = get_deployment_service()
    result = await deployment_service.rollback(project.name)

    if result.get("status") == "rolled_back":
        project.status = ProjectStatus.ROLLED_BACK
        session.add(project)
        session.commit()

    return result


@router.get("/{project_id}/deployment/status")
async def get_deployment_status(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Get the current deployment status for a product."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deployment_service = get_deployment_service()
    return await deployment_service.get_deployment_status(project.name)


@router.get("/{project_id}/deployment/history")
def get_deployment_history(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    """Get the deployment history for a product."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    deployment_service = get_deployment_service()
    history = deployment_service.get_deployment_history(project.name)

    return {
        "project_id": project_id,
        "project_name": project.name,
        "deployments": history,
    }
