# app/models/user.py
from tortoise import Model, fields
from datetime import datetime, timezone


class User(Model):
    """
    User model for authentication and authorization.
    """

    id = fields.UUIDField(pk=True)
    email = fields.CharField(max_length=255, unique=True, index=True, null=True)
    phone = fields.CharField(max_length=20, unique=True, index=True, null=True)
    username = fields.CharField(max_length=100, unique=True, index=True, null=True)
    is_active = fields.BooleanField(default=True)
    is_verified = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    businesses: fields.ReverseRelation["Business"]
    sessions: fields.ReverseRelation["Session"]
    verification_codes: fields.ReverseRelation["VerificationCode"]

    class Meta:
        table = "users"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        identifier = self.email or self.phone or self.username
        return f"User {identifier}"


class Session(Model):
    """
    Session model for managing user sessions.
    """

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="sessions")
    session_token_hash = fields.CharField(max_length=64, unique=True, index=True)
    expires_at = fields.DatetimeField()
    created_at = fields.DatetimeField(auto_now_add=True)
    last_activity = fields.DatetimeField(auto_now=True)
    user_agent = fields.TextField(null=True)
    ip_address = fields.CharField(max_length=45, null=True)

    class Meta:
        table = "sessions"
        ordering = ["-created_at"]

    def is_expired(self) -> bool:
        """
        Check if session is expired.

        Returns:
            True if session is expired, False otherwise
        """
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def __str__(self) -> str:
        return f"Session for user {self.user.id} (expires: {self.expires_at})"


class VerificationCode(Model):
    """
    Verification code for passwordless authentication.
    """

    id = fields.UUIDField(pk=True)
    user = fields.ForeignKeyField(
        "models.User",
        related_name="verification_codes",
        null=True
    )
    contact = fields.CharField(max_length=255, index=True)
    contact_type = fields.CharField(max_length=10)
    code_hash = fields.CharField(max_length=64)
    expires_at = fields.DatetimeField()
    attempts = fields.IntField(default=0)
    is_used = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "verification_codes"
        ordering = ["-created_at"]

    def is_expired(self) -> bool:
        """
        Check if verification code is expired.

        Returns:
            True if code is expired, False otherwise
        """
        now = datetime.now(timezone.utc)
        expires_at = self.expires_at

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        return now > expires_at

    def __str__(self) -> str:
        return f"Code for {self.contact} ({self.contact_type})"