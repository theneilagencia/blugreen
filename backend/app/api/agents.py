from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.database import get_session
from app.models.agent import Agent, AgentRead, AgentType

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentRead])
def list_agents(
    session: Session = Depends(get_session),
) -> list[Agent]:
    agents = session.exec(select(Agent)).all()
    return list(agents)


@router.get("/types")
def get_agent_types() -> list[dict[str, str]]:
    return [
        {
            "type": AgentType.ARCHITECT.value,
            "name": "Architect Agent",
            "description": "Defines structure and boundaries, never writes final code",
        },
        {
            "type": AgentType.BACKEND.value,
            "name": "Backend Agent",
            "description": "Creates APIs, models database, writes tests",
        },
        {
            "type": AgentType.FRONTEND.value,
            "name": "Frontend Agent",
            "description": "Creates functional UI, does not create complex design",
        },
        {
            "type": AgentType.INFRA.value,
            "name": "Infra Agent",
            "description": "Handles Docker, CI/CD, and deployment",
        },
        {
            "type": AgentType.QA.value,
            "name": "QA Agent",
            "description": "Runs tests, tries to break the system, blocks deploy if fails",
        },
        {
            "type": AgentType.UX.value,
            "name": "UX Agent",
            "description": "Evaluates flows, detects friction, simplifies paths",
        },
        {
            "type": AgentType.UI_REFINEMENT.value,
            "name": "UI Refinement Agent",
            "description": "Improves visual hierarchy, spacing, readability, microcopy",
        },
    ]


@router.get("/{agent_type}", response_model=AgentRead)
def get_agent(
    agent_type: AgentType,
    session: Session = Depends(get_session),
) -> Agent:
    agent = session.exec(select(Agent).where(Agent.agent_type == agent_type)).first()

    if not agent:
        agent = Agent(
            name=f"{agent_type.value}_agent",
            agent_type=agent_type,
        )
        session.add(agent)
        session.commit()
        session.refresh(agent)

    return agent


@router.get("/{agent_type}/capabilities")
def get_agent_capabilities(agent_type: AgentType) -> dict[str, list[str]]:
    capabilities_map = {
        AgentType.ARCHITECT: [
            "define_structure",
            "create_boundaries",
            "design_architecture",
            "plan_modules",
            "define_contracts",
        ],
        AgentType.BACKEND: [
            "create_apis",
            "model_database",
            "write_tests",
            "implement_business_logic",
            "create_endpoints",
        ],
        AgentType.FRONTEND: [
            "create_functional_ui",
            "implement_components",
            "connect_to_api",
            "handle_state",
            "implement_routing",
        ],
        AgentType.INFRA: [
            "create_docker_config",
            "setup_cicd",
            "configure_deployment",
            "manage_environments",
            "setup_monitoring",
        ],
        AgentType.QA: [
            "run_tests",
            "break_system",
            "validate_quality",
            "block_deploy",
            "report_issues",
        ],
        AgentType.UX: [
            "evaluate_flows",
            "detect_friction",
            "simplify_paths",
            "reject_confusing_ux",
            "validate_ux_rules",
        ],
        AgentType.UI_REFINEMENT: [
            "improve_visual_hierarchy",
            "adjust_spacing",
            "improve_readability",
            "refine_microcopy",
            "ensure_consistency",
        ],
    }

    restrictions_map = {
        AgentType.ARCHITECT: [
            "never_write_final_code",
            "never_implement_features",
            "never_modify_existing_code",
        ],
        AgentType.BACKEND: [
            "never_modify_frontend",
            "never_change_infrastructure",
            "never_skip_tests",
        ],
        AgentType.FRONTEND: [
            "never_create_complex_design",
            "never_modify_backend",
            "never_violate_design_system",
            "only_use_allowed_components",
        ],
        AgentType.INFRA: [
            "never_use_paid_services",
            "never_expose_secrets",
            "never_execute_destructive_commands",
            "never_hardcode_env_vars",
        ],
        AgentType.QA: [
            "never_approve_without_tests",
            "never_skip_validation",
            "never_ignore_failures",
        ],
        AgentType.UX: [
            "never_alter_ui",
            "never_alter_colors",
            "never_alter_layout",
            "never_change_visual_design",
        ],
        AgentType.UI_REFINEMENT: [
            "never_violate_design_system",
            "never_alter_flow",
            "never_change_functionality",
            "only_use_design_tokens",
        ],
    }

    return {
        "capabilities": capabilities_map.get(agent_type, []),
        "restrictions": restrictions_map.get(agent_type, []),
    }
