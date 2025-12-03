# app/exceptions/auth_exceptions.py
class AuthException(Exception):
    """Base exception for authentication errors."""
    pass


class InvalidCredentialsError(AuthException):
    """Raised when credentials are invalid."""

    def __init__(self, message: str = "Invalid credentials"):
        super().__init__(message)


class SessionExpiredError(AuthException):
    """Raised when session is expired."""

    def __init__(self, message: str = "Session has expired"):
        super().__init__(message)


class InvalidSessionError(AuthException):
    """Raised when session is invalid."""

    def __init__(self, message: str = "Invalid session"):
        super().__init__(message)


class UserNotActiveError(AuthException):
    """Raised when user account is not active."""

    def __init__(self, message: str = "User account is not active"):
        super().__init__(message)


class InvalidVerificationCodeError(AuthException):
    """Raised when verification code is invalid."""

    def __init__(self, message: str = "Invalid verification code"):
        super().__init__(message)


class VerificationCodeExpiredError(AuthException):
    """Raised when verification code is expired."""

    def __init__(self, message: str = "Verification code has expired"):
        super().__init__(message)


class TooManyAttemptsError(AuthException):
    """Raised when too many verification attempts."""

    def __init__(self, message: str = "Too many attempts. Please request a new code"):
        super().__init__(message)


class CodeAlreadyUsedError(AuthException):
    """Raised when verification code was already used."""

    def __init__(self, message: str = "This code has already been used"):
        super().__init__(message)


class RateLimitError(AuthException):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Too many requests. Please try again later"):
        super().__init__(message)