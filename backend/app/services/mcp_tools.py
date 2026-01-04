"""
MCP Tools for Create Flow

Provides auditable tools for agents to interact with the workspace:
- repo_read: Read files from workspace
- repo_write: Write files to workspace
- shell_run: Execute allowlisted shell commands

All operations are logged and auditable.
"""

import logging
import os
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

logger = logging.getLogger(__name__)


# Allowlist of safe shell commands
SHELL_ALLOWLIST = [
    "pytest",
    "ruff",
    "mypy",
    "npm test",
    "npm run build",
    "npm run lint",
    "poetry run pytest",
    "poetry run ruff",
    "poetry run mypy",
]


class ToolCall(BaseModel):
    """Record of a tool call for auditability."""
    
    tool_name: str
    inputs: Dict[str, Any]
    outputs: Dict[str, Any]
    error: Optional[str] = None
    duration_ms: Optional[float] = None


class MCPTools:
    """
    MCP Tools for agent interactions.
    
    All operations are auditable and logged.
    """
    
    def __init__(self, workspace_root: str):
        """
        Initialize MCP tools.
        
        Args:
            workspace_root: Root directory for workspace operations
        """
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.tool_calls: List[ToolCall] = []
    
    def repo_read(self, file_path: str) -> Dict[str, Any]:
        """
        Read a file from the workspace.
        
        Args:
            file_path: Relative path to file within workspace
        
        Returns:
            Dict with file content and metadata
        """
        import time
        start_time = time.time()
        
        try:
            full_path = self.workspace_root / file_path
            
            # Security: Ensure path is within workspace
            if not self._is_safe_path(full_path):
                raise ValueError(f"Path {file_path} is outside workspace")
            
            if not full_path.exists():
                raise FileNotFoundError(f"File {file_path} not found")
            
            content = full_path.read_text()
            
            result = {
                "content": content,
                "path": file_path,
                "size": len(content),
            }
            
            # Log tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="repo_read",
                inputs={"file_path": file_path},
                outputs={"size": len(content)},
                duration_ms=duration_ms,
            ))
            
            return result
        
        except Exception as e:
            logger.error(f"repo_read failed: {e}")
            
            # Log failed tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="repo_read",
                inputs={"file_path": file_path},
                outputs={},
                error=str(e),
                duration_ms=duration_ms,
            ))
            
            raise
    
    def repo_write(
        self,
        file_path: str,
        content: str,
        create_dirs: bool = True,
    ) -> Dict[str, Any]:
        """
        Write a file to the workspace.
        
        Args:
            file_path: Relative path to file within workspace
            content: File content to write
            create_dirs: Create parent directories if needed
        
        Returns:
            Dict with file metadata and diff
        """
        import time
        start_time = time.time()
        
        try:
            full_path = self.workspace_root / file_path
            
            # Security: Ensure path is within workspace
            if not self._is_safe_path(full_path):
                raise ValueError(f"Path {file_path} is outside workspace")
            
            # Read existing content for diff
            old_content = None
            if full_path.exists():
                old_content = full_path.read_text()
            
            # Create parent directories
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            full_path.write_text(content)
            
            # Generate diff for auditability
            diff = self._generate_diff(old_content, content, file_path)
            
            result = {
                "path": file_path,
                "size": len(content),
                "diff": diff,
                "created": old_content is None,
            }
            
            # Log tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="repo_write",
                inputs={"file_path": file_path, "size": len(content)},
                outputs={"created": old_content is None},
                duration_ms=duration_ms,
            ))
            
            return result
        
        except Exception as e:
            logger.error(f"repo_write failed: {e}")
            
            # Log failed tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="repo_write",
                inputs={"file_path": file_path},
                outputs={},
                error=str(e),
                duration_ms=duration_ms,
            ))
            
            raise
    
    def shell_run(
        self,
        command: str,
        timeout: int = 30,
        cwd: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Execute an allowlisted shell command.
        
        Args:
            command: Shell command to execute (must be in allowlist)
            timeout: Command timeout in seconds
            cwd: Working directory (relative to workspace)
        
        Returns:
            Dict with command output and exit code
        """
        import time
        start_time = time.time()
        
        try:
            # Security: Check allowlist
            if not self._is_command_allowed(command):
                raise ValueError(
                    f"Command not in allowlist: {command}\n"
                    f"Allowed commands: {', '.join(SHELL_ALLOWLIST)}"
                )
            
            # Determine working directory
            work_dir = self.workspace_root
            if cwd:
                work_dir = self.workspace_root / cwd
                if not self._is_safe_path(work_dir):
                    raise ValueError(f"Working directory {cwd} is outside workspace")
            
            # Execute command
            result = subprocess.run(
                command,
                shell=True,
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            
            output = {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "command": command,
            }
            
            # Log tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="shell_run",
                inputs={"command": command, "cwd": cwd or "."},
                outputs={"exit_code": result.returncode},
                duration_ms=duration_ms,
            ))
            
            return output
        
        except subprocess.TimeoutExpired:
            logger.error(f"shell_run timeout: {command}")
            
            # Log failed tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="shell_run",
                inputs={"command": command},
                outputs={},
                error=f"Timeout after {timeout}s",
                duration_ms=duration_ms,
            ))
            
            raise TimeoutError(f"Command timed out after {timeout}s: {command}")
        
        except Exception as e:
            logger.error(f"shell_run failed: {e}")
            
            # Log failed tool call
            duration_ms = (time.time() - start_time) * 1000
            self.tool_calls.append(ToolCall(
                tool_name="shell_run",
                inputs={"command": command},
                outputs={},
                error=str(e),
                duration_ms=duration_ms,
            ))
            
            raise
    
    def get_tool_calls(self) -> List[Dict[str, Any]]:
        """Get all tool calls for auditability."""
        return [call.model_dump() for call in self.tool_calls]
    
    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within workspace (security check)."""
        try:
            path.resolve().relative_to(self.workspace_root.resolve())
            return True
        except ValueError:
            return False
    
    def _is_command_allowed(self, command: str) -> bool:
        """Check if command is in allowlist."""
        command_lower = command.lower().strip()
        
        for allowed in SHELL_ALLOWLIST:
            if command_lower.startswith(allowed.lower()):
                return True
        
        return False
    
    def _generate_diff(
        self,
        old_content: Optional[str],
        new_content: str,
        file_path: str,
    ) -> str:
        """Generate unified diff for auditability."""
        import difflib
        
        if old_content is None:
            return f"+++ {file_path} (new file)\n{new_content[:500]}"
        
        old_lines = old_content.splitlines(keepends=True)
        new_lines = new_content.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm="",
        )
        
        # Limit diff size for auditability
        diff_text = "\n".join(list(diff)[:100])
        
        if len(diff_text) > 2000:
            diff_text = diff_text[:2000] + "\n... (diff truncated)"
        
        return diff_text
