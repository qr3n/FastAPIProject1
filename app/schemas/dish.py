# app/schemas/dish.py
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional


class DishCreateSchema(BaseModel):
    """Schema for creating a new dish."""

    business_id: str = Field(..., description="Business UUID")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    price: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    image: str = Field(..., description="Base64 encoded image")
    is_available: bool = True

    @field_validator('price')
    @classmethod
    def validate_price(cls, value: str) -> str:
        """Validate price."""
        price_decimal = Decimal(value)
        if price_decimal <= 0:
            raise ValueError('Price must be positive')
        if price_decimal > Decimal('9999999.99'):
            raise ValueError('Price is too large')
        return value

    @field_validator('image')
    @classmethod
    def validate_image(cls, value: str) -> str:
        """Validate image."""
        if not value.startswith('data:image/'):
            raise ValueError('Image must be a valid base64 data URL')
        return value


class DishUpdateSchema(BaseModel):
    """Schema for updating a dish."""

    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    price: Optional[str] = Field(None, pattern=r'^\d+(\.\d{1,2})?$')
    image: Optional[str] = Field(None, description="Base64 encoded image")
    is_available: Optional[bool] = None

    @field_validator('price')
    @classmethod
    def validate_price(cls, value: Optional[str]) -> Optional[str]:
        """Validate price if provided."""
        if value is None:
            return value
        price_decimal = Decimal(value)
        if price_decimal <= 0:
            raise ValueError('Price must be positive')
        if price_decimal > Decimal('9999999.99'):
            raise ValueError('Price is too large')
        return value

    @field_validator('image')
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        """Validate image if provided."""
        if value is None:
            return value
        if not value.startswith('data:image/'):
            raise ValueError('Image must be a valid base64 data URL')
        return value


class DishResponseSchema(BaseModel):
    """Schema for dish responses."""

    id: str
    business_id: str
    title: str
    description: str
    price: str
    image: str
    is_available: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_dish(cls, dish: 'Dish', base_url: str) -> 'DishResponseSchema':
        """
        Create response schema from ORM model.

        Args:
            dish: Dish ORM model
            base_url: Base URL for serving images

        Returns:
            DishResponseSchema instance
        """
        return cls(
            id=str(dish.id),
            business_id=str(dish.business_id),
            title=dish.title,
            description=dish.description,
            price=str(dish.price),
            image=f"{base_url}/uploads/{dish.image_path}",
            is_available=dish.is_available,
            created_at=dish.created_at.isoformat(),
            updated_at=dish.updated_at.isoformat()
        )