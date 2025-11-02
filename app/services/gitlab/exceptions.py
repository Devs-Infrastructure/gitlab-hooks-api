"""GitLab API exceptions."""


class GitLabAPIError(Exception):
    """Base exception for GitLab API errors."""

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class GitLabAuthenticationError(GitLabAPIError):
    """Raised when GitLab authentication fails."""

    def __init__(self, message: str = "Authentication failed"):
        super().__init__(message, status_code=401)

