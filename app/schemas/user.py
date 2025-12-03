# app/schemas/user.py
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID

from app.core.security import is_valid_phone, normalize_phone


class SendCodeSchema(BaseModel):
    """Schema for sending verification code."""

    contact: str = Field(..., description="Email or phone number")

    @field_validator('contact')
    @classmethod
    def validate_contact(cls, value: str) -> str:
        """
        Validate contact is either email or phone.

        Args:
            value: Contact value

        Returns:
            Validated contact

        Raises:
            ValueError: If contact is neither valid email nor phone
        """
        from app.core.security import is_valid_email

        if '@' in value:
            if not is_valid_email(value):
                raise ValueError('Invalid email format')
            return value.lower()
        else:
            if not is_valid_phone(value):
                raise ValueError('Invalid phone format')
            return normalize_phone(value)


class VerifyCodeSchema(BaseModel):
    """Schema for verifying code and logging in."""

    contact: str = Field(..., description="Email or phone number")
    code: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator('contact')
    @classmethod
    def validate_contact(cls, value: str) -> str:
        """
        Validate and normalize contact.

        Args:
            value: Contact value

        Returns:
            Validated contact

        Raises:
            ValueError: If contact is invalid
        """
        from app.core.security import is_valid_email

        if '@' in value:
            if not is_valid_email(value):
                raise ValueError('Invalid email format')
            return value.lower()
        else:
            if not is_valid_phone(value):
                raise ValueError('Invalid phone format')
            return normalize_phone(value)

    @field_validator('code')
    @classmethod
    def validate_code(cls, value: str) -> str:
        """
        Validate code is 6 digits.

        Args:
            value: Verification code

        Returns:
            Validated code

        Raises:
            ValueError: If code is not 6 digits
        """
        if not value.isdigit():
            raise ValueError('Code must contain only digits')
        return value


class UserResponseSchema(BaseModel):
    """Schema for user responses."""

    id: UUID
    email: Optional[str]
    phone: Optional[str]
    username: Optional[str]
    is_active: bool
    is_verified: bool
    created_at: datetime

    @classmethod
    def from_orm_user(cls, user) -> "UserResponseSchema":
        """
        Create schema from User ORM model.

        Args:
            user: User model instance

        Returns:
            UserResponseSchema instance
        """
        return cls(
            id=user.id,
            email=user.email,
            phone=user.phone,
            username=user.username,
            is_active=user.is_active,
            is_verified=user.is_verified,
            created_at=user.created_at
        )


class SessionInfoSchema(BaseModel):
    """Schema for session information."""

    id: UUID
    created_at: datetime
    last_activity: datetime
    expires_at: datetime
    user_agent: Optional[str]
    ip_address: Optional[str]

    @classmethod
    def from_orm_session(cls, session) -> "SessionInfoSchema":
        """
        Create schema from Session ORM model.

        Args:
            session: Session model instance

        Returns:
            SessionInfoSchema instance
        """
        return cls(
            id=session.id,
            created_at=session.created_at,
            last_activity=session.last_activity,
            expires_at=session.expires_at,
            user_agent=session.user_agent,
            ip_address=session.ip_address
        )