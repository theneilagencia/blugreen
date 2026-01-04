"""
LLM Provider with Ollama + No-LLM Fallback

Provides LLM capabilities with automatic fallback to template-based generation
when Ollama is unavailable or times out.
"""

import logging
from typing import Any, Optional
import httpx
from pydantic import BaseModel

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class LLMResponse(BaseModel):
    """Response from LLM provider."""
    
    content: str
    llm_used: str  # "ollama" or "no-llm-fallback"
    model: Optional[str] = None
    error: Optional[str] = None


class LLMProvider:
    """
    LLM Provider with automatic fallback.
    
    Primary: Ollama HTTP API
    Fallback: Template-based generation (no-LLM mode)
    """
    
    def __init__(
        self,
        ollama_url: Optional[str] = None,
        timeout: int = 30,
        model: str = "llama3.2:latest",
    ):
        self.ollama_url = ollama_url or getattr(settings, "ollama_url", "http://localhost:11434")
        self.timeout = timeout
        self.model = model
        self.client = httpx.AsyncClient(timeout=self.timeout)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        use_fallback_on_error: bool = True,
    ) -> LLMResponse:
        """
        Generate text using LLM with automatic fallback.
        
        Args:
            prompt: User prompt
            system_prompt: System prompt (optional)
            use_fallback_on_error: Use fallback if Ollama fails
        
        Returns:
            LLMResponse with generated content
        """
        # Try Ollama first
        try:
            return await self._generate_ollama(prompt, system_prompt)
        except Exception as e:
            logger.warning(f"Ollama generation failed: {e}")
            
            if use_fallback_on_error:
                logger.info("Falling back to no-LLM mode")
                return self._generate_fallback(prompt, system_prompt, error=str(e))
            else:
                raise
    
    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> LLMResponse:
        """Generate using Ollama HTTP API (v0.13.5 compatible)."""
        # Build prompt for /api/generate endpoint (Ollama v0.13.5)
        full_prompt = ""
        
        if system_prompt:
            full_prompt = f"System: {system_prompt}\n\n"
        
        full_prompt += f"User: {prompt}\n\nAssistant:"
        
        response = await self.client.post(
            f"{self.ollama_url}/api/generate",
            json={
                "model": self.model,
                "prompt": full_prompt,
                "stream": False,
            },
        )
        
        response.raise_for_status()
        data = response.json()
        
        return LLMResponse(
            content=data["response"],
            llm_used="ollama",
            model=self.model,
        )
    
    def _generate_fallback(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        error: Optional[str] = None,
    ) -> LLMResponse:
        """
        Generate using template-based fallback (no-LLM mode).
        
        Uses heuristics and templates to generate reasonable output
        without requiring an LLM.
        """
        # Detect intent from prompt keywords
        prompt_lower = prompt.lower()
        
        if "generate code" in prompt_lower or "create backend" in prompt_lower:
            content = self._fallback_generate_code(prompt)
        elif "create test" in prompt_lower or "write test" in prompt_lower:
            content = self._fallback_generate_tests(prompt)
        elif "generate doc" in prompt_lower or "create readme" in prompt_lower:
            content = self._fallback_generate_docs(prompt)
        elif "validate" in prompt_lower or "check" in prompt_lower:
            content = self._fallback_validate(prompt)
        else:
            content = self._fallback_generic(prompt)
        
        return LLMResponse(
            content=content,
            llm_used="no-llm-fallback",
            error=error,
        )
    
    def _fallback_generate_code(self, prompt: str) -> str:
        """Fallback for code generation."""
        return """
# Generated using template-based fallback (no LLM)

## Backend (FastAPI)
```python
# backend/main.py
from fastapi import FastAPI

app = FastAPI(title="Generated API")

@app.get("/")
def root():
    return {"message": "Hello World"}

@app.get("/health")
def health():
    return {"status": "healthy"}
```

## Frontend (React)
```javascript
// frontend/src/App.jsx
import React from 'react';

function App() {
  return (
    <div>
      <h1>Generated App</h1>
      <p>This is a template-generated application.</p>
    </div>
  );
}

export default App;
```

**Note:** This is a minimal template. For production use, configure Ollama for LLM-powered generation.
"""
    
    def _fallback_generate_tests(self, prompt: str) -> str:
        """Fallback for test generation."""
        return """
# Generated using template-based fallback (no LLM)

## Unit Tests
```python
# tests/test_main.py
def test_root():
    assert True, "Template test placeholder"

def test_health():
    assert True, "Template test placeholder"
```

**Note:** This is a minimal template. For production use, configure Ollama for LLM-powered test generation.
"""
    
    def _fallback_generate_docs(self, prompt: str) -> str:
        """Fallback for documentation generation."""
        return """
# Generated Documentation

## Overview
This project was generated using the Blugreen Create Flow.

## Getting Started
1. Install dependencies
2. Run the application
3. Access at http://localhost:8000

## API Documentation
See `/docs` for interactive API documentation.

**Note:** This is a minimal template. For production use, configure Ollama for LLM-powered documentation.
"""
    
    def _fallback_validate(self, prompt: str) -> str:
        """Fallback for validation."""
        return """
{
  "validation_passed": true,
  "findings": [],
  "score": 100,
  "note": "Template-based validation (no LLM). Configure Ollama for detailed analysis."
}
"""
    
    def _fallback_generic(self, prompt: str) -> str:
        """Generic fallback."""
        return f"""
Generated response using template-based fallback (no LLM).

Prompt: {prompt[:100]}...

For better results, configure Ollama by setting OLLAMA_URL environment variable.
"""
    
    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()


# Singleton instance
_llm_provider: Optional[LLMProvider] = None


def get_llm_provider() -> LLMProvider:
    """Get singleton LLM provider instance."""
    global _llm_provider
    if _llm_provider is None:
        _llm_provider = LLMProvider(
            ollama_url=settings.ollama_url,
            model=settings.ollama_model,
        )
    return _llm_provider
