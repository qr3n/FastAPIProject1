# app/services/business_media_service.py
import base64
import uuid
from pathlib import Path
from typing import List, Optional
from PIL import Image
import io

from shared.models.business_media import BusinessMedia, MediaType
from shared.models.business import Business
from shared.models.user import User
from app.schemas.business_media import (
    BusinessMediaCreateSchema,
    BusinessMediaUpdateSchema
)
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError,
    BusinessMediaNotFoundError
)
from app.exceptions.dish_exceptions import (
    InvalidImageError,
    ImageSaveError
)
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


class BusinessMediaService:
    """Service for managing business media content."""

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
    def _delete_image_from_disk(image_path: str) -> None:
        """
        Delete image file from disk.

        Args:
            image_path: Relative path to image file
        """
        try:
            file_path = Path(settings.UPLOAD_DIR) / image_path
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            logger.warning(f"Failed to delete image {image_path}: {str(e)}")

    @staticmethod
    async def _get_business_and_verify_access(business_id: str, user: User) -> Business:
        """
        Get business and verify user has access.

        Args:
            business_id: Business UUID
            user: User making the request

        Returns:
            Business instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        business = await Business.get_or_none(id=business_id)
        if not business:
            raise BusinessNotFoundError(business_id)

        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        return business

    @staticmethod
    async def create_media(
            business_id: str,
            media_data: BusinessMediaCreateSchema,
            user: User
    ) -> BusinessMedia:
        """
        Create new business media.

        Args:
            business_id: Business UUID
            media_data: Media creation data including base64 image
            user: User creating the media

        Returns:
            Created BusinessMedia instance

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
            InvalidImageError: If image is invalid
            ImageSaveError: If image cannot be saved
        """
        business = await BusinessMediaService._get_business_and_verify_access(business_id, user)

        # Decode and save image
        image_bytes, image_format = BusinessMediaService._decode_base64_image(media_data.image)
        image_filename = BusinessMediaService._save_image_to_disk(image_bytes, image_format)

        # Create media record
        media = await BusinessMedia.create(
            business=business,
            media_type=media_data.media_type,
            title=media_data.title,
            description=media_data.description,
            image_path=image_filename,
            sort_order=media_data.sort_order
        )

        logger.info(f"Created media {media.id} for business {business_id}")
        return media

    @staticmethod
    async def get_media_by_id(media_id: str) -> BusinessMedia:
        """
        Get media by ID.

        Args:
            media_id: Media UUID

        Returns:
            BusinessMedia instance

        Raises:
            BusinessMediaNotFoundError: If media doesn't exist
        """
        media = await BusinessMedia.get_or_none(id=media_id).prefetch_related("business")
        if not media:
            raise BusinessMediaNotFoundError(media_id)
        return media

    @staticmethod
    async def get_business_media(
            business_id: str,
            media_type: Optional[MediaType] = None,
            is_active: Optional[bool] = None
    ) -> List[BusinessMedia]:
        """
        Get all media for a business.

        Args:
            business_id: Business UUID
            media_type: Optional filter by media type
            is_active: Optional filter by active status

        Returns:
            List of BusinessMedia instances
        """
        query = BusinessMedia.filter(business_id=business_id)

        if media_type is not None:
            query = query.filter(media_type=media_type)

        if is_active is not None:
            query = query.filter(is_active=is_active)

        return await query.order_by("sort_order", "-created_at").all()

    @staticmethod
    async def update_media(
            media_id: str,
            media_data: BusinessMediaUpdateSchema,
            user: User
    ) -> BusinessMedia:
        """
        Update existing media.

        Args:
            media_id: Media UUID
            media_data: Updated media data
            user: User updating the media

        Returns:
            Updated BusinessMedia instance

        Raises:
            BusinessMediaNotFoundError: If media doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
            InvalidImageError: If new image is invalid
            ImageSaveError: If new image cannot be saved
        """
        media = await BusinessMediaService.get_media_by_id(media_id)

        # Verify access
        if media.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}

        if media_data.media_type is not None:
            update_fields['media_type'] = media_data.media_type

        if media_data.title is not None:
            update_fields['title'] = media_data.title

        if media_data.description is not None:
            update_fields['description'] = media_data.description

        if media_data.sort_order is not None:
            update_fields['sort_order'] = media_data.sort_order

        if media_data.is_active is not None:
            update_fields['is_active'] = media_data.is_active

        # Handle image update
        if media_data.image is not None:
            # Delete old image
            BusinessMediaService._delete_image_from_disk(media.image_path)

            # Save new image
            image_bytes, image_format = BusinessMediaService._decode_base64_image(media_data.image)
            image_filename = BusinessMediaService._save_image_to_disk(image_bytes, image_format)
            update_fields['image_path'] = image_filename

        if update_fields:
            await media.update_from_dict(update_fields).save()
            await media.refresh_from_db()

        logger.info(f"Updated media {media_id}")
        return media

    @staticmethod
    async def delete_media(media_id: str, user: User) -> None:
        """
        Delete media.

        Args:
            media_id: Media UUID
            user: User deleting the media

        Raises:
            BusinessMediaNotFoundError: If media doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
        """
        media = await BusinessMediaService.get_media_by_id(media_id)

        # Verify access
        if media.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        # Delete image file
        BusinessMediaService._delete_image_from_disk(media.image_path)

        # Delete record
        await media.delete()

        logger.info(f"Deleted media {media_id}")

    @staticmethod
    async def reorder_media(
            business_id: str,
            media_ids: List[str],
            user: User
    ) -> List[BusinessMedia]:
        """
        Reorder media items for a business.

        Args:
            business_id: Business UUID
            media_ids: List of media IDs in desired order
            user: User reordering the media

        Returns:
            List of updated BusinessMedia instances

        Raises:
            BusinessNotFoundError: If business doesn't exist
            BusinessAccessDeniedError: If user doesn't own the business
            BusinessMediaNotFoundError: If any media doesn't exist
        """
        # Verify business access
        await BusinessMediaService._get_business_and_verify_access(business_id, user)

        # Update sort order for each media
        updated_media = []
        for index, media_id in enumerate(media_ids):
            media = await BusinessMedia.get_or_none(id=media_id, business_id=business_id)
            if not media:
                raise BusinessMediaNotFoundError(media_id)

            media.sort_order = index
            await media.save()
            updated_media.append(media)

        logger.info(f"Reordered {len(media_ids)} media items for business {business_id}")
        return updated_media
