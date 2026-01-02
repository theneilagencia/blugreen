from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.database import get_session
from app.models.project import Project
from app.models.workflow import Workflow, WorkflowRead, WorkflowStep, WorkflowStepRead
from app.workflows import MainWorkflow, UXUIRefinementWorkflow

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/", response_model=list[WorkflowRead])
def list_workflows(
    project_id: int | None = None,
    session: Session = Depends(get_session),
) -> list[Workflow]:
    query = select(Workflow)
    if project_id:
        query = query.where(Workflow.project_id == project_id)
    return list(session.exec(query).all())


@router.get("/{workflow_id}", response_model=WorkflowRead)
def get_workflow(
    workflow_id: int,
    session: Session = Depends(get_session),
) -> Workflow:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return workflow


@router.get("/{workflow_id}/steps", response_model=list[WorkflowStepRead])
def get_workflow_steps(
    workflow_id: int,
    session: Session = Depends(get_session),
) -> list[WorkflowStep]:
    steps = session.exec(
        select(WorkflowStep)
        .where(WorkflowStep.workflow_id == workflow_id)
        .order_by(WorkflowStep.order)
    ).all()
    return list(steps)


@router.post("/project/{project_id}/main")
def create_main_workflow(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workflow = MainWorkflow(session, project)
    workflow.initialize()
    return workflow.start()


@router.post("/project/{project_id}/ux-ui-refinement")
def create_ux_ui_refinement_workflow(
    project_id: int,
    session: Session = Depends(get_session),
) -> dict:
    project = session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    workflow = UXUIRefinementWorkflow(session, project)
    workflow.initialize()
    return workflow.start()


@router.get("/{workflow_id}/status")
def get_workflow_status(
    workflow_id: int,
    session: Session = Depends(get_session),
) -> dict:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    project = session.get(Project, workflow.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    main_workflow = MainWorkflow(session, project)
    main_workflow.workflow = workflow
    return main_workflow.get_status()


@router.post("/{workflow_id}/advance")
def advance_workflow(
    workflow_id: int,
    success: bool = True,
    error_message: str | None = None,
    session: Session = Depends(get_session),
) -> dict:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    project = session.get(Project, workflow.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    main_workflow = MainWorkflow(session, project)
    main_workflow.workflow = workflow
    return main_workflow.advance_step(success, error_message)


@router.post("/{workflow_id}/rollback")
def rollback_workflow(
    workflow_id: int,
    session: Session = Depends(get_session),
) -> dict:
    workflow = session.get(Workflow, workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    project = session.get(Project, workflow.project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    main_workflow = MainWorkflow(session, project)
    main_workflow.workflow = workflow
    return main_workflow.rollback()
