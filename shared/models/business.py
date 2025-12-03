from tortoise import Model, fields
from enum import Enum


class BusinessType(str, Enum):
    """Enum for business types."""

    RESTAURANT = "restaurant"
    PARKING = "parking"
    RETAIL = "retail"
    SERVICE = "service"
    OTHER = "other"


class Business(Model):
    """
    Business model representing a business with a Telegram bot.
    """

    id = fields.UUIDField(pk=True)
    owner = fields.ForeignKeyField("models.User", related_name="businesses")
    name = fields.CharField(max_length=255)
    description = fields.TextField()
    business_type = fields.CharEnumField(BusinessType)
    telegram_bot_token = fields.CharField(max_length=500)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    dishes: fields.ReverseRelation["Dish"]

    class Meta:
        table = "businesses"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.business_type})"