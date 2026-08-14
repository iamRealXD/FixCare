from typing import Any


class AppException(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status_code: int = 500,
        details: dict[str, Any] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class ValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details,
        )


class AuthenticationError(AppException):
    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            code="AUTHENTICATION_ERROR",
            message=message,
            status_code=401,
        )


class AuthorizationError(AppException):
    def __init__(self, message: str = "Insufficient permissions"):
        super().__init__(
            code="AUTHORIZATION_ERROR",
            message=message,
            status_code=403,
        )


class NotFoundError(AppException):
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            code="NOT_FOUND",
            message=f"{resource} not found",
            status_code=404,
            details={"resource": resource, "identifier": identifier},
        )


class AIProviderError(AppException):
    def __init__(self, message: str, provider: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="AI_PROVIDER_ERROR",
            message=message,
            status_code=502,
            details={"provider": provider, **(details or {})},
        )


class AIResponseValidationError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="AI_RESPONSE_VALIDATION_ERROR",
            message=message,
            status_code=502,
            details=details,
        )


class SafetyEscalationError(AppException):
    def __init__(self, message: str, risk_level: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="SAFETY_ESCALATION",
            message=message,
            status_code=400,
            details={"risk_level": risk_level, **(details or {})},
        )


class DatabaseError(AppException):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="DATABASE_ERROR",
            message=message,
            status_code=500,
            details=details,
        )


class ExternalServiceError(AppException):
    def __init__(self, service: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(
            code="EXTERNAL_SERVICE_ERROR",
            message=f"{service}: {message}",
            status_code=502,
            details={"service": service, **(details or {})},
        )


class RateLimitError(AppException):
    def __init__(self, message: str = "Rate limit exceeded"):
        super().__init__(
            code="RATE_LIMIT_EXCEEDED",
            message=message,
            status_code=429,
        )