"""Domain and Application level exceptions."""


class ApplicationError(Exception):
    """Base exception for all application and domain errors."""

    def __init__(self, message: str = "Ocorreu um erro na aplicação.", code: str | None = None):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__

    def __str__(self) -> str:
        return self.message


class BusinessRuleViolationError(ApplicationError):
    """Raised when a business rule or invariant is violated."""


class PermissionDeniedError(ApplicationError):
    """Raised when an action is not authorized by the RBAC / permission system."""


class NotFoundError(ApplicationError):
    """Raised when a requested domain entity is not found."""


class ValidationError(ApplicationError):
    """Raised when domain validation fails."""
