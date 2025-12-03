# app/schemas/businesses.py
from pydantic import BaseModel, Field
from typing import Optional
from app.models.business import BusinessType


class BusinessCreateSchema(BaseModel):
    """Schema for creating a new business."""

    name: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=2000)
    business_type: BusinessType
    telegram_bot_token: str = Field(..., min_length=10)


class BusinessUpdateSchema(BaseModel):
    """Schema for updating a business."""

    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    business_type: Optional[BusinessType] = None
    telegram_bot_token: Optional[str] = Field(None, min_length=10)
    is_active: Optional[bool] = None


class BusinessResponseSchema(BaseModel):
    """Schema for business responses."""

    id: str
    owner_id: str
    name: str
    description: str
    business_type: str
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_business(cls, business: 'Business') -> 'BusinessResponseSchema':
        """
        Create response schema from ORM model.

        Args:
            business: Business ORM model

        Returns:
            BusinessResponseSchema instance
        """
        return cls(
            id=str(business.id),
            owner_id=str(business.owner_id),
            name=business.name,
            description=business.description,
            business_type=business.business_type.value,
            is_active=business.is_active,
            created_at=business.created_at.isoformat(),
            updated_at=business.updated_at.isoformat()
        )