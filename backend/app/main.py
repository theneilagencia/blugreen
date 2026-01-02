from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (
    agents_router,
    projects_router,
    quality_router,
    system_router,
    tasks_router,
    workflows_router,
)
from app.config import get_settings
from app.database import create_db_and_tables

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    create_db_and_tables()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Autonomous Engineering Platform - Build, refine, and deploy SaaS products autonomously",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(workflows_router)
app.include_router(quality_router)
app.include_router(system_router)


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}
