"""
API endpoints for managing project-agent associations.

Provides endpoints for:
- Assigning agents to projects
- Listing agents assigned to a project
- Updating agent roles and scopes
- Removing agents from projects
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.agent import Agent
from app.models.project import Project
from app.models.project_agent import (
    ProjectAgent,
    ProjectAgentCreate,
    ProjectAgentRead,
    ProjectAgentUpdate,
)

router = APIRouter(prefix="/projects/{project_id}/agents", tags=["project-agents"])


@router.post("/", response_model=ProjectAgentRead)
def assign_agent_to_project(
    project_id: int,
    assignment: ProjectAgentCreate,
    session: Session = Depends(get_session),
) -> ProjectAgent:
    """Assign an agent to a project."""
    # Validate project exists
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate agent exists
    agent = session.get(Agent, assignment.agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    # Check if already assigned
    existing = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == assignment.agent_id,
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Agent {agent.name} is already assigned to this project",
        )

    # Create assignment
    db_assignment = ProjectAgent.model_validate(assignment)
    db_assignment.project_id = project_id
    session.add(db_assignment)
    session.commit()
    session.refresh(db_assignment)

    return db_assignment


@router.get("/", response_model=list[ProjectAgentRead])
def list_project_agents(
    project_id: int,
    active_only: bool = True,
    session: Session = Depends(get_session),
) -> list[ProjectAgent]:
    """List all agents assigned to a project."""
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    query = select(ProjectAgent).where(ProjectAgent.project_id == project_id)

    if active_only:
        query = query.where(ProjectAgent.is_active == True)  # noqa: E712

    return list(session.exec(query).all())


@router.get("/{agent_id}", response_model=ProjectAgentRead)
def get_project_agent(
    project_id: int,
    agent_id: int,
    session: Session = Depends(get_session),
) -> ProjectAgent:
    """Get a specific agent assignment for a project."""
    assignment = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Agent assignment not found",
        )

    return assignment


@router.patch("/{agent_id}", response_model=ProjectAgentRead)
def update_project_agent(
    project_id: int,
    agent_id: int,
    update: ProjectAgentUpdate,
    session: Session = Depends(get_session),
) -> ProjectAgent:
    """Update an agent assignment (role, scope, active status)."""
    assignment = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Agent assignment not found",
        )

    update_data = update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(assignment, key, value)

    assignment.last_activity_at = datetime.utcnow()
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    return assignment


@router.delete("/{agent_id}")
def remove_agent_from_project(
    project_id: int,
    agent_id: int,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    """Remove an agent from a project."""
    assignment = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Agent assignment not found",
        )

    session.delete(assignment)
    session.commit()

    return {"message": "Agent removed from project"}


@router.post("/{agent_id}/deactivate")
def deactivate_project_agent(
    project_id: int,
    agent_id: int,
    session: Session = Depends(get_session),
) -> ProjectAgentRead:
    """Deactivate an agent assignment (soft delete)."""
    assignment = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Agent assignment not found",
        )

    assignment.is_active = False
    assignment.last_activity_at = datetime.utcnow()
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    return assignment


@router.post("/{agent_id}/activate")
def activate_project_agent(
    project_id: int,
    agent_id: int,
    session: Session = Depends(get_session),
) -> ProjectAgentRead:
    """Activate a previously deactivated agent assignment."""
    assignment = session.exec(
        select(ProjectAgent).where(
            ProjectAgent.project_id == project_id,
            ProjectAgent.agent_id == agent_id,
        )
    ).first()

    if not assignment:
        raise HTTPException(
            status_code=404,
            detail="Agent assignment not found",
        )

    assignment.is_active = True
    assignment.last_activity_at = datetime.utcnow()
    session.add(assignment)
    session.commit()
    session.refresh(assignment)

    return assignment
