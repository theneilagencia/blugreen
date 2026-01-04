"""
Debug endpoints for testing Ollama integration
"""

from fastapi import APIRouter, HTTPException
import httpx
from app.config import get_settings
from app.services.llm_provider import get_llm_provider

router = APIRouter(prefix="/debug", tags=["debug"])
settings = get_settings()


@router.get("/ollama/models")
async def ollama_models():
    """List available Ollama models."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{settings.ollama_base_url}/api/tags")
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list models: {str(e)}")


@router.post("/ollama/preload")
async def ollama_preload_model(model: str = None):
    """Preload a model into memory by sending an empty generate request."""
    model_name = model or settings.ollama_model
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            # Send empty request to preload model
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": model_name,
                    "prompt": "",
                    "keep_alive": "10m",
                },
            )
            response.raise_for_status()
            return {
                "status": "success",
                "message": f"Model {model_name} preloaded",
                "model": model_name,
            }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "model": model_name,
        }


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
    """Test Ollama generation (v0.13.5 compatible)."""
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": prompt,
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
            "url": f"{settings.ollama_base_url}/api/generate",
        }


@router.post("/llm/test-fallback")
async def test_llm_fallback(prompt: str = "Generate code for a simple API"):
    """
    Test LLM fallback mode by forcing Ollama to fail.
    """
    try:
        provider = get_llm_provider()
        # Force fallback by using invalid Ollama URL
        provider.ollama_url = "http://invalid-ollama-host:99999"
        response = await provider.generate(prompt=prompt, use_fallback_on_error=True)
        
        return {
            "status": "success",
            "llm_used": response.llm_used,
            "content_preview": response.content[:200] + "...",
            "error": response.error,
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }
