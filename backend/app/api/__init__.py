from app.api.agents import router as agents_router
from app.api.projects import router as projects_router
from app.api.quality import router as quality_router
from app.api.system import router as system_router
from app.api.tasks import router as tasks_router
from app.api.workflows import router as workflows_router

__all__ = [
    "projects_router",
    "tasks_router",
    "agents_router",
    "workflows_router",
    "quality_router",
    "system_router",
]
