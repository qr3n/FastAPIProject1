class DishException(Exception):
    """Base exception for dish-related errors."""
    pass


class DishNotFoundError(DishException):
    """Raised when dish is not found in database."""

    def __init__(self, dish_id: str):
        self.dish_id = dish_id
        super().__init__(f"Dish with id {dish_id} not found")


class InvalidImageError(DishException):
    """Raised when image data is invalid."""

    def __init__(self, message: str = "Invalid image data"):
        super().__init__(message)


class ImageSaveError(DishException):
    """Raised when image cannot be saved to disk."""

    def __init__(self, message: str = "Failed to save image"):
        super().__init__(message)