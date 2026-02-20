# app/schemas/business_media.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from shared.models.business_media import MediaType


class BusinessMediaCreateSchema(BaseModel):
    """Schema for creating business media."""

    media_type: MediaType = Field(default=MediaType.OTHER, description="Type of media content")
    title: Optional[str] = Field(None, max_length=255, description="Media title")
    description: Optional[str] = Field(None, max_length=1000, description="Media description")
    image: str = Field(..., description="Base64 encoded image")
    sort_order: int = Field(default=0, ge=0, description="Sort order for display")

    @field_validator('image')
    @classmethod
    def validate_image(cls, value: str) -> str:
        """Validate image is a valid base64 data URL."""
        if not value.startswith('data:image/'):
            raise ValueError('Image must be a valid base64 data URL')
        return value

    @field_validator('title', 'description')
    @classmethod
    def validate_text_fields(cls, value: Optional[str]) -> Optional[str]:
        """Strip whitespace from text fields."""
        if value:
            return value.strip()
        return value


class BusinessMediaUpdateSchema(BaseModel):
    """Schema for updating business media."""

    model_config = {"extra": "forbid"}

    media_type: Optional[MediaType] = Field(None, description="Type of media content")
    title: Optional[str] = Field(None, max_length=255, description="Media title")
    description: Optional[str] = Field(None, max_length=1000, description="Media description")
    image: Optional[str] = Field(None, description="Base64 encoded image")
    sort_order: Optional[int] = Field(None, ge=0, description="Sort order for display")
    is_active: Optional[bool] = Field(None, description="Whether media is active")

    @field_validator('image')
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        """Validate image if provided."""
        if value is None:
            return value
        if not value.startswith('data:image/'):
            raise ValueError('Image must be a valid base64 data URL')
        return value

    @field_validator('title', 'description')
    @classmethod
    def validate_text_fields(cls, value: Optional[str]) -> Optional[str]:
        """Strip whitespace from text fields."""
        if value:
            return value.strip()
        return value


class BusinessMediaResponseSchema(BaseModel):
    """Schema for business media responses."""

    id: str
    business_id: str
    media_type: str
    title: Optional[str]
    description: Optional[str]
    image_url: str
    sort_order: int
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_media(cls, media: 'BusinessMedia', base_url: str) -> 'BusinessMediaResponseSchema':
        """
        Create response schema from ORM model.

        Args:
            media: BusinessMedia ORM model
            base_url: Base URL for serving images

        Returns:
            BusinessMediaResponseSchema instance
        """
        return cls(
            id=str(media.id),
            business_id=str(media.business_id),
            media_type=media.media_type.value,
            title=media.title,
            description=media.description,
            image_url=f"{base_url}/uploads/{media.image_path}",
            sort_order=media.sort_order,
            is_active=media.is_active,
            created_at=media.created_at.isoformat(),
            updated_at=media.updated_at.isoformat()
        )


class MediaReorderSchema(BaseModel):
    """Schema for reordering media items."""

    media_ids: List[str] = Field(..., min_length=1, description="List of media IDs in desired order")
