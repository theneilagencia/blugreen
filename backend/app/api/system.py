from fastapi import APIRouter

from app.services.ollama import get_ollama_client

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/ollama/status")
async def get_ollama_status() -> dict:
    """Check if Ollama LLM service is available and get model info."""
    client = get_ollama_client()

    is_available = await client.is_available()

    if not is_available:
        return {
            "status": "unavailable",
            "message": "Ollama service is not running or not reachable",
            "base_url": client.base_url,
            "model": client.model,
            "models_available": [],
        }

    try:
        models = await client.list_models()
        model_configured = client.model in models

        return {
            "status": "available",
            "base_url": client.base_url,
            "model": client.model,
            "model_configured": model_configured,
            "models_available": models,
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e),
            "base_url": client.base_url,
            "model": client.model,
        }


@router.get("/llm/health")
async def llm_health_check() -> dict:
    """Simple health check for LLM availability."""
    client = get_ollama_client()
    is_available = await client.is_available()

    return {
        "llm_available": is_available,
        "provider": "ollama",
        "model": client.model,
    }
