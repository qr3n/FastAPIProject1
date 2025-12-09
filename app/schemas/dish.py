# app/schemas/dish.py
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional, List


class DishCreateSchema(BaseModel):
    """Schema for creating a new dish."""

    business_id: str = Field(..., description="Business UUID")
    title: str = Field(..., min_length=3, max_length=100)
    description: str = Field(..., min_length=10, max_length=500)
    price: str = Field(..., pattern=r'^\d+(\.\d{1,2})?$')
    image: str = Field(..., description="Base64 encoded image")
    is_available: bool = True

    # Новые поля
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")
    category: Optional[str] = Field(None, max_length=50, description="Dish category")
    cuisine: Optional[str] = Field(None, max_length=50, description="Cuisine type")
    ingredients: List[str] = Field(default_factory=list, description="Main ingredients")
    allergens: List[str] = Field(default_factory=list, description="Known allergens")

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

    @field_validator('tags', 'ingredients', 'allergens')
    @classmethod
    def validate_list_items(cls, value: List[str]) -> List[str]:
        """Validate and normalize list items."""
        return [item.strip().lower() for item in value if item.strip()]

    @field_validator('category', 'cuisine')
    @classmethod
    def validate_text_fields(cls, value: Optional[str]) -> Optional[str]:
        """Normalize text fields."""
        if value:
            return value.strip().lower()
        return value


class DishUpdateSchema(BaseModel):
    """Schema for updating a dish."""

    title: Optional[str] = Field(None, min_length=3, max_length=100)
    description: Optional[str] = Field(None, min_length=10, max_length=500)
    price: Optional[str] = Field(None, pattern=r'^\d+(\.\d{1,2})?$')
    image: Optional[str] = Field(None, description="Base64 encoded image")
    is_available: Optional[bool] = None

    # Новые поля
    tags: Optional[List[str]] = Field(None, description="Tags for categorization")
    category: Optional[str] = Field(None, max_length=50, description="Dish category")
    cuisine: Optional[str] = Field(None, max_length=50, description="Cuisine type")
    ingredients: Optional[List[str]] = Field(None, description="Main ingredients")
    allergens: Optional[List[str]] = Field(None, description="Known allergens")

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

    @field_validator('tags', 'ingredients', 'allergens')
    @classmethod
    def validate_list_items(cls, value: Optional[List[str]]) -> Optional[List[str]]:
        """Validate and normalize list items."""
        if value is None:
            return value
        return [item.strip().lower() for item in value if item.strip()]

    @field_validator('category', 'cuisine')
    @classmethod
    def validate_text_fields(cls, value: Optional[str]) -> Optional[str]:
        """Normalize text fields."""
        if value:
            return value.strip().lower()
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
    tags: List[str]
    category: Optional[str]
    cuisine: Optional[str]
    ingredients: List[str]
    allergens: List[str]
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
            tags=dish.tags or [],
            category=dish.category,
            cuisine=dish.cuisine,
            ingredients=dish.ingredients or [],
            allergens=dish.allergens or [],
            created_at=dish.created_at.isoformat(),
            updated_at=dish.updated_at.isoformat()
        )