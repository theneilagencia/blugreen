"""
Custom exceptions for Blugreen application.
"""


class CouldNotDetectBranchError(Exception):
    """Raised when the default branch cannot be detected from a Git repository."""

    def __init__(
        self,
        message: str,
        repository_url: str,
        attempted_branches: list[str] | None = None,
        available_branches: list[str] | None = None,
    ):
        self.repository_url = repository_url
        self.attempted_branches = attempted_branches or []
        self.available_branches = available_branches or []
        super().__init__(message)
