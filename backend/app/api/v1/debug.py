"""
Debug endpoints for testing Ollama integration
"""

from fastapi import APIRouter, HTTPException
import httpx
from app.config import get_settings

router = APIRouter(prefix="/debug", tags=["debug"])
settings = get_settings()


@router.get("/ollama/models")
async def list_ollama_models():
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/ollama/pull/{model_name}")
async def pull_ollama_model(model_name: str):
    """Pull an Ollama model."""
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/pull",
                json={"name": model_name},
            )
            response.raise_for_status()
            return {"status": "success", "model": model_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to pull model: {str(e)}")


@router.get("/ollama/status")
async def ollama_status():
    """Check Ollama connection status."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            return {
                "status": "connected",
                "url": settings.ollama_base_url,
                "status_code": response.status_code,
            }
    except Exception as e:
        return {
            "status": "disconnected",
            "url": settings.ollama_base_url,
            "error": str(e),
        }


@router.post("/ollama/test-generate")
async def test_ollama_generate(prompt: str = "Say hello in one sentence"):
    """Test Ollama generation."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": settings.ollama_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                },
            )
            response.raise_for_status()
            return {
                "status": "success",
                "model": settings.ollama_model,
                "response": response.json(),
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model": settings.ollama_model,
            "url": f"{settings.ollama_base_url}/api/chat",
        }
