"""
# shared/models/tg_user.py
User model for storing Telegram users.
"""
from tortoise import fields
from tortoise.models import Model


class TGUser(Model):
    """
    Telegram user model.

    Stores user information and preferences.
    """
    id = fields.IntField(pk=True)
    telegram_id = fields.BigIntField(unique=True, index=True)
    username = fields.CharField(max_length=255, null=True)
    first_name = fields.CharField(max_length=255, null=True)
    last_name = fields.CharField(max_length=255, null=True)
    language_code = fields.CharField(max_length=10, default="ru")
    thread_id = fields.CharField(max_length=255, null=True)

    # Timestamps
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_interaction = fields.DatetimeField(null=True)

    # Status
    is_active = fields.BooleanField(default=True)
    is_blocked = fields.BooleanField(default=False)

    class Meta:
        table = "users"

    def __str__(self):
        return f"User {self.telegram_id} ({self.first_name})"

    @property
    def full_name(self):
        """Get user's full name."""
        parts = [self.first_name, self.last_name]
        return " ".join(filter(None, parts)) or f"User {self.telegram_id}"