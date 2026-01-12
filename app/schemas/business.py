# app/schemas/businesses.py
from pydantic import BaseModel, Field
from typing import Optional, List
from shared.models.business import BusinessType


class BusinessCreateSchema(BaseModel):
    """Schema for creating a new business."""

    name: str = Field(..., min_length=3, max_length=255)
    description: str = Field(..., min_length=10, max_length=2000)
    business_type: BusinessType
    telegram_bot_token: str = Field(..., min_length=10)


class BusinessUpdateSchema(BaseModel):
    """Schema for updating a business."""

    model_config = {"extra": "forbid"}

    name: Optional[str] = Field(None, min_length=3, max_length=255)
    description: Optional[str] = Field(None, min_length=10, max_length=2000)
    is_active: Optional[bool] = None


class TableInfoSchema(BaseModel):
    """Schema for table information."""

    id: str
    table_number: int
    capacity: int
    floor: int
    status: str
    is_active: bool


class DishInfoSchema(BaseModel):
    """Schema for dish information."""

    id: str
    title: str
    description: str
    price: str
    category: Optional[str]
    cuisine: Optional[str]
    is_available: bool
    tags: List[str]


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

    # Дополнительная информация
    tables_count: Optional[int] = None
    dishes_count: Optional[int] = None
    tables: Optional[List[TableInfoSchema]] = None
    dishes: Optional[List[DishInfoSchema]] = None

    model_config = {"from_attributes": True}

    @classmethod
    async def from_orm_business(
            cls,
            business: 'Business',
            include_tables: bool = False,
            include_dishes: bool = False
    ) -> 'BusinessResponseSchema':
        """
        Create response schema from ORM model.

        Args:
            business: Business ORM model
            include_tables: Include full tables list
            include_dishes: Include full dishes list

        Returns:
            BusinessResponseSchema instance
        """
        from shared.models.table import Table
        from shared.models.dish import Dish

        # Базовые данные
        data = {
            "id": str(business.id),
            "owner_id": str(business.owner_id),
            "name": business.name,
            "description": business.description,
            "business_type": business.business_type.value,
            "is_active": business.is_active,
            "created_at": business.created_at.isoformat(),
            "updated_at": business.updated_at.isoformat()
        }

        # Подсчет столиков
        tables_count = await Table.filter(business=business).count()
        data["tables_count"] = tables_count

        # Подсчет блюд
        dishes_count = await Dish.filter(business=business).count()
        data["dishes_count"] = dishes_count

        # Полный список столиков (если запрошено)
        if include_tables:
            tables = await Table.filter(business=business).all()
            data["tables"] = [
                TableInfoSchema(
                    id=str(table.id),
                    table_number=table.table_number,
                    capacity=table.capacity,
                    floor=table.floor,
                    status=table.status.value,
                    is_active=table.is_active
                )
                for table in tables
            ]

        # Полный список блюд (если запрошено)
        if include_dishes:
            dishes = await Dish.filter(business=business).all()
            data["dishes"] = [
                DishInfoSchema(
                    id=str(dish.id),
                    title=dish.title,
                    description=dish.description,
                    price=str(dish.price),
                    category=dish.category,
                    cuisine=dish.cuisine,
                    is_available=dish.is_available,
                    tags=dish.tags if dish.tags else []
                )
                for dish in dishes
            ]

        return cls(**data)