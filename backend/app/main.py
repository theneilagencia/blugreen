import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

from app.api import (
    agents_router,
    assumption_router,
    create_router,
    debug_router,
    guided_router,
    intent_router,
    metrics_router,
    product_router,
    project_agents_router,
    projects_router,
    quality_router,
    system_router,
    tasks_router,
    workflows_router,
)
from app.config import get_settings
from app.database import create_db_and_tables
from app.exception_handlers import (
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

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

# Ensure app.blugreen.com.br is always allowed
cors_origins = list(settings.cors_origins) if settings.cors_origins else []
if "https://app.blugreen.com.br" not in cors_origins:
    cors_origins.append("https://app.blugreen.com.br")
    logger.info("Added https://app.blugreen.com.br to CORS origins")
if "https://blugreen.com.br" not in cors_origins:
    cors_origins.append("https://blugreen.com.br")
    logger.info("Added https://blugreen.com.br to CORS origins")

logger.info(f"Configuring CORS with origins: {cors_origins}")

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logger.info("CORS middleware configured successfully")

# EMERGENCY CORS AIRBAG
# This is NOT a design pattern. This is a safety net.
# Ensures CORS headers are ALWAYS present, even if exceptions escape.
@app.middleware("http")
async def force_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault(
        "Access-Control-Allow-Origin",
        "https://app.blugreen.com.br"
    )
    response.headers.setdefault(
        "Access-Control-Allow-Credentials",
        "true"
    )
    return response

# Add exception handlers that preserve CORS headers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

logger.info("Exception handlers configured")

app.include_router(projects_router)
app.include_router(tasks_router)
app.include_router(agents_router)
app.include_router(project_agents_router)
app.include_router(metrics_router)
app.include_router(workflows_router)
app.include_router(quality_router)
app.include_router(system_router)
app.include_router(product_router)
app.include_router(assumption_router)
app.include_router(create_router)
app.include_router(debug_router)
app.include_router(guided_router)
app.include_router(intent_router)


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
