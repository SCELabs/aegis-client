class AegisError(Exception):
    """Base exception for Aegis client errors."""


class AegisAPIError(AegisError):
    """Raised when the Aegis API returns an error response."""

    def __init__(self, message: str, status_code: int | None = None):
        self.status_code = status_code
        super().__init__(message)


class AegisConnectionError(AegisError):
    """Raised when the client cannot connect to the Aegis API."""


class AegisTimeoutError(AegisError):
    """Raised when the request to the Aegis API times out."""
