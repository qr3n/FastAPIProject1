# app/services/dish_service.py
import base64
import uuid
from pathlib import Path
from decimal import Decimal
from typing import List, Optional
from PIL import Image
import io

from app.models.dish import Dish
from app.models.business import Business
from app.models.user import User
from app.schemas.dish import DishCreateSchema, DishUpdateSchema
from app.exceptions.dish_exceptions import (
    DishNotFoundError,
    InvalidImageError,
    ImageSaveError
)
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError
)
from app.core.config import settings


class DishService:
    """Service for managing dishes business logic."""

    @staticmethod
    async def get_all_dishes(business_id: Optional[str] = None) -> List[Dish]:
        """
        Retrieve all dishes, optionally filtered by business.

        Args:
            business_id: Optional business UUID to filter by

        Returns:
            List of dishes
        """
        if business_id:
            return await Dish.filter(business_id=business_id).all()
        return await Dish.all()

    @staticmethod
    async def get_dish_by_id(dish_id: str) -> Dish:
        """
        Retrieve a single dish by ID.

        Args:
            dish_id: UUID of the dish

        Returns:
            Dish instance

        Raises:
            DishNotFoundError: If dish doesn't exist
        """
        dish = await Dish.get_or_none(id=dish_id).prefetch_related("business")
        if not dish:
            raise DishNotFoundError(dish_id)
        return dish

    @staticmethod
    def _decode_base64_image(base64_string: str) -> tuple[bytes, str]:
        """
        Decode base64 image string and extract format.

        Args:
            base64_string: Base64 encoded image with data URL prefix

        Returns:
            Tuple of (image_bytes, image_format)

        Raises:
            InvalidImageError: If base64 string is invalid
        """
        try:
            if not base64_string.startswith('data:image/'):
                raise InvalidImageError("Image must be a data URL")

            header, encoded = base64_string.split(',', 1)
            image_format = header.split('/')[1].split(';')[0]

            if image_format not in ['jpeg', 'jpg', 'png', 'webp']:
                raise InvalidImageError(f"Unsupported image format: {image_format}")

            image_bytes = base64.b64decode(encoded)

            if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
                raise InvalidImageError(
                    f"Image size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
                )

            return image_bytes, image_format

        except Exception as e:
            if isinstance(e, InvalidImageError):
                raise
            raise InvalidImageError(f"Failed to decode image: {str(e)}")

    @staticmethod
    def _save_image_to_disk(image_bytes: bytes, image_format: str) -> str:
        """
        Save image bytes to disk with validation.

        Args:
            image_bytes: Raw image bytes
            image_format: Image format (jpeg, png, webp)

        Returns:
            Relative path to saved image

        Raises:
            ImageSaveError: If image cannot be saved
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            img = Image.open(io.BytesIO(image_bytes))

            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{uuid.uuid4()}.{image_format}"
            file_path = upload_dir / filename

            img.save(file_path, format=image_format.upper())

            return filename

        except Exception as e:
            raise ImageSaveError(f"Failed to save image: {str(e)}")

    @staticmethod
    async def create_dish(dish_data: DishCreateSchema, user: User) -> Dish:
        """
        Create a new dish with image upload.

        Args:
            dish_data: Dish creation data including base64 image
            user: User creating the dish

        Returns:
            Created dish instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
            InvalidImageError: If image is invalid
            ImageSaveError: If image cannot be saved
        """
        business = await Business.get_or_none(id=dish_data.business_id)
        if not business:
            raise BusinessNotFoundError(dish_data.business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        image_bytes, image_format = DishService._decode_base64_image(dish_data.image)
        image_filename = DishService._save_image_to_disk(image_bytes, image_format)

        dish = await Dish.create(
            business=business,
            title=dish_data.title,
            description=dish_data.description,
            price=Decimal(dish_data.price),
            image_path=image_filename,
            is_available=dish_data.is_available
        )

        return dish

    @staticmethod
    async def update_dish(dish_id: str, dish_data: DishUpdateSchema, user: User) -> Dish:
        """
        Update an existing dish.

        Args:
            dish_id: UUID of the dish to update
            dish_data: Updated dish data
            user: User updating the dish

        Returns:
            Updated dish instance

        Raises:
            DishNotFoundError: If dish doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
            InvalidImageError: If new image is invalid
            ImageSaveError: If new image cannot be saved
        """
        dish = await DishService.get_dish_by_id(dish_id)

        if dish.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}

        if dish_data.title is not None:
            update_fields['title'] = dish_data.title

        if dish_data.description is not None:
            update_fields['description'] = dish_data.description

        if dish_data.price is not None:
            update_fields['price'] = Decimal(dish_data.price)

        if dish_data.is_available is not None:
            update_fields['is_available'] = dish_data.is_available

        if dish_data.image is not None:
            old_image_path = Path(settings.UPLOAD_DIR) / dish.image_path
            if old_image_path.exists():
                old_image_path.unlink()

            image_bytes, image_format = DishService._decode_base64_image(dish_data.image)
            image_filename = DishService._save_image_to_disk(image_bytes, image_format)
            update_fields['image_path'] = image_filename

        await dish.update_from_dict(update_fields).save()
        await dish.refresh_from_db()

        return dish

    @staticmethod
    async def delete_dish(dish_id: str, user: User) -> None:
        """
        Delete a dish and its associated image.

        Args:
            dish_id: UUID of the dish to delete
            user: User deleting the dish

        Raises:
            DishNotFoundError: If dish doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        dish = await DishService.get_dish_by_id(dish_id)

        if dish.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        image_path = Path(settings.UPLOAD_DIR) / dish.image_path
        if image_path.exists():
            image_path.unlink()

        await dish.delete()