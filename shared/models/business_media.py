# shared/models/business_media.py
from tortoise import Model, fields
from enum import Enum


class MediaType(str, Enum):
    """Enum for business media types."""

    INTERIOR = "interior"      # Интерьер заведения
    KITCHEN = "kitchen"        # Кухня
    TEAM = "team"              # Коллектив/персонал
    FOOD = "food"              # Еда/блюда (общие фото)
    EXTERIOR = "exterior"      # Экстерьер/фасад
    ATMOSPHERE = "atmosphere"  # Атмосфера
    OTHER = "other"            # Другое


class BusinessMedia(Model):
    """
    Business media model representing images and media content for a business.
    """

    id = fields.UUIDField(pk=True)
    business = fields.ForeignKeyField("models.Business", related_name="media")
    media_type = fields.CharEnumField(MediaType, default=MediaType.OTHER)
    title = fields.CharField(max_length=255, null=True)
    description = fields.TextField(null=True)
    image_path = fields.CharField(max_length=500)
    sort_order = fields.IntField(default=0)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "business_media"
        ordering = ["sort_order", "-created_at"]

    def __str__(self) -> str:
        return f"{self.media_type.value}: {self.title or 'Untitled'}"
