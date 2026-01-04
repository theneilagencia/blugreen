"""
Tests for AgentRunner and LLMProvider
"""

import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from app.services.agent_runner import AgentRunner
from app.services.llm_provider import LLMProvider, LLMResponse
from app.services.mcp_tools import MCPTools


@pytest.fixture
def temp_workspace():
    """Create temporary workspace for tests."""
    workspace = tempfile.mkdtemp()
    yield workspace
    shutil.rmtree(workspace)


@pytest.fixture
def agent_runner(temp_workspace):
    """Create AgentRunner instance for tests."""
    return AgentRunner(temp_workspace)


@pytest.fixture
def mcp_tools(temp_workspace):
    """Create MCPTools instance for tests."""
    return MCPTools(temp_workspace)


# LLMProvider Tests

@pytest.mark.asyncio
async def test_llm_provider_fallback():
    """Test LLMProvider fallback when Ollama is unavailable."""
    # Use invalid URL to force fallback
    provider = LLMProvider(ollama_url="http://invalid:9999", timeout=1)
    
    response = await provider.generate("Generate code for a FastAPI app")
    
    assert response.llm_used == "no-llm-fallback"
    assert response.content is not None
    assert len(response.content) > 0
    assert response.error is not None  # Should have error from Ollama failure


@pytest.mark.asyncio
async def test_llm_provider_fallback_code_generation():
    """Test fallback code generation."""
    provider = LLMProvider(ollama_url="http://invalid:9999", timeout=1)
    
    response = await provider.generate("Generate code for a backend API")
    
    assert "FastAPI" in response.content or "backend" in response.content.lower()
    assert "```python" in response.content or "def " in response.content


@pytest.mark.asyncio
async def test_llm_provider_fallback_test_generation():
    """Test fallback test generation."""
    provider = LLMProvider(ollama_url="http://invalid:9999", timeout=1)
    
    response = await provider.generate("Create tests for the API")
    
    assert "test" in response.content.lower()
    assert "```python" in response.content or "def test_" in response.content


# MCPTools Tests

def test_mcp_tools_repo_write(mcp_tools, temp_workspace):
    """Test repo_write creates files correctly."""
    result = mcp_tools.repo_write("test.txt", "Hello World")
    
    assert result["path"] == "test.txt"
    assert result["size"] == 11
    assert result["created"] is True
    
    # Verify file exists
    file_path = Path(temp_workspace) / "test.txt"
    assert file_path.exists()
    assert file_path.read_text() == "Hello World"


def test_mcp_tools_repo_read(mcp_tools, temp_workspace):
    """Test repo_read reads files correctly."""
    # Create file first
    mcp_tools.repo_write("test.txt", "Hello World")
    
    # Read file
    result = mcp_tools.repo_read("test.txt")
    
    assert result["content"] == "Hello World"
    assert result["path"] == "test.txt"
    assert result["size"] == 11


def test_mcp_tools_repo_write_with_diff(mcp_tools, temp_workspace):
    """Test repo_write generates diff for existing files."""
    # Create initial file
    mcp_tools.repo_write("test.txt", "Hello World")
    
    # Update file
    result = mcp_tools.repo_write("test.txt", "Hello Universe")
    
    assert result["created"] is False
    assert "diff" in result
    assert len(result["diff"]) > 0


def test_mcp_tools_shell_run_allowlist(mcp_tools):
    """Test shell_run only allows allowlisted commands."""
    # Allowed command
    result = mcp_tools.shell_run("pytest --version")
    assert result["exit_code"] is not None
    
    # Disallowed command
    with pytest.raises(ValueError, match="not in allowlist"):
        mcp_tools.shell_run("rm -rf /")


def test_mcp_tools_path_security(mcp_tools, temp_workspace):
    """Test path security prevents directory traversal."""
    with pytest.raises(ValueError, match="outside workspace"):
        mcp_tools.repo_write("../../../etc/passwd", "hacked")


def test_mcp_tools_tool_calls_audit(mcp_tools):
    """Test tool calls are audited."""
    mcp_tools.repo_write("test.txt", "Hello")
    mcp_tools.repo_read("test.txt")
    
    tool_calls = mcp_tools.get_tool_calls()
    
    assert len(tool_calls) == 2
    assert tool_calls[0]["tool_name"] == "repo_write"
    assert tool_calls[1]["tool_name"] == "repo_read"
    assert "duration_ms" in tool_calls[0]


# AgentRunner Tests

@pytest.mark.asyncio
async def test_agent_runner_generate_code(agent_runner, temp_workspace):
    """Test generate_code step."""
    context = {
        "product_name": "Test Product",
        "stack": "FastAPI, React",
        "objective": "Create a test application",
    }
    
    output = await agent_runner.run("generate_code", context)
    
    assert "llm_used" in output
    assert "files_changed" in output
    assert "tool_calls" in output
    assert len(output["files_changed"]) > 0
    
    # Verify files were created
    for file_path in output["files_changed"]:
        full_path = Path(temp_workspace) / file_path
        assert full_path.exists()


@pytest.mark.asyncio
async def test_agent_runner_create_tests(agent_runner, temp_workspace):
    """Test create_tests step."""
    context = {
        "product_name": "Test Product",
    }
    
    output = await agent_runner.run("create_tests", context)
    
    assert "llm_used" in output
    assert "files_changed" in output
    assert "test_results" in output
    assert len(output["files_changed"]) > 0


@pytest.mark.asyncio
async def test_agent_runner_generate_docs(agent_runner, temp_workspace):
    """Test generate_docs step."""
    context = {
        "product_name": "Test Product",
        "stack": "FastAPI, React",
        "objective": "Create a test application",
    }
    
    output = await agent_runner.run("generate_docs", context)
    
    assert "llm_used" in output
    assert "files_changed" in output
    assert len(output["files_changed"]) > 0
    
    # Verify README was created
    readme_path = Path(temp_workspace) / "README.md"
    assert readme_path.exists()


@pytest.mark.asyncio
async def test_agent_runner_validate_structure(agent_runner, temp_workspace):
    """Test validate_structure step."""
    # Create some files first
    agent_runner.mcp_tools.repo_write("README.md", "# Test")
    agent_runner.mcp_tools.repo_write("backend/main.py", "# Backend")
    agent_runner.mcp_tools.repo_write("frontend/src/App.jsx", "// Frontend")
    
    context = {
        "product_name": "Test Product",
    }
    
    output = await agent_runner.run("validate_structure", context)
    
    assert "llm_used" in output
    assert "validation_passed" in output
    assert "findings" in output
    assert "score" in output


@pytest.mark.asyncio
async def test_agent_runner_finalize_product(agent_runner):
    """Test finalize_product step."""
    context = {
        "product_name": "Test Product",
        "previous_outputs": {
            "generate_code": {"files_changed": ["backend/main.py"]},
            "create_tests": {"test_results": {"passed": True}},
            "validate_structure": {"score": 95},
        },
    }
    
    output = await agent_runner.run("finalize_product", context)
    
    assert "llm_used" in output
    assert output["llm_used"] == "none"  # No LLM for finalize
    assert "summary" in output
    assert "version_tag" in output
    assert "Test Product" in output["summary"]


@pytest.mark.asyncio
async def test_agent_runner_idempotency(agent_runner, temp_workspace):
    """Test that steps 1-4 are idempotent."""
    context = {
        "product_name": "Test Product",
        "stack": "FastAPI, React",
        "objective": "Create a test application",
    }
    
    # Run generate_code twice
    output1 = await agent_runner.run("generate_code", context)
    output2 = await agent_runner.run("generate_code", context)
    
    # Should produce similar results
    assert output1["llm_used"] == output2["llm_used"]
    assert len(output1["files_changed"]) == len(output2["files_changed"])


@pytest.mark.asyncio
async def test_agent_runner_with_ollama_unavailable(agent_runner):
    """Test that agent runner works when Ollama is unavailable."""
    # Force LLM provider to use fallback
    agent_runner.llm_provider.ollama_url = "http://invalid:9999"
    agent_runner.llm_provider.timeout = 1
    
    context = {
        "product_name": "Test Product",
        "stack": "FastAPI, React",
        "objective": "Create a test application",
    }
    
    # Should still work with fallback
    output = await agent_runner.run("generate_code", context)
    
    assert output["llm_used"] == "no-llm-fallback"
    assert len(output["files_changed"]) > 0
