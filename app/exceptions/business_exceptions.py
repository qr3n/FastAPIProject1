# app/exceptions/business_exceptions.py
class BusinessException(Exception):
    """Base exception for business-related errors."""
    pass


class BusinessNotFoundError(BusinessException):
    """Raised when business is not found."""

    def __init__(self, business_id: str):
        self.business_id = business_id
        super().__init__(f"Business with id {business_id} not found")


class BusinessAccessDeniedError(BusinessException):
    """Raised when user doesn't have access to business."""

    def __init__(self, message: str = "Access to this business is denied"):
        super().__init__(message)


class InvalidTelegramTokenError(BusinessException):
    """Raised when Telegram bot token is invalid."""

    def __init__(self, message: str = "Invalid Telegram bot token"):
        super().__init__(message)