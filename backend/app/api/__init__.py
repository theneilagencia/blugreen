from app.api.agents import router as agents_router
from app.api.assumption import router as assumption_router
from app.api.create import router as create_router
from app.api.metrics import router as metrics_router
from app.api.product import router as product_router
from app.api.project_agents import router as project_agents_router
from app.api.projects import router as projects_router
from app.api.quality import router as quality_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.workflows import router as workflows_router

__all__ = [
    "projects_router",
    "tasks_router",
    "agents_router",
    "project_agents_router",
    "metrics_router",
    "workflows_router",
    "quality_router",
    "system_router",
    "product_router",
    "assumption_router",
    "create_router",
]
