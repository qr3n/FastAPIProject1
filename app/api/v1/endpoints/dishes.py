# app/api/v1/endpoints/dishes.py
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import List, Optional

from app.schemas.dish import (
    DishCreateSchema,
    DishUpdateSchema,
    DishResponseSchema, DishSearchSchema
)
from app.services.dish_service import DishService
from app.api.v1.dependencies.auth import get_current_user
from shared.models.user import User
from app.exceptions.dish_exceptions import (
    DishNotFoundError,
    InvalidImageError,
    ImageSaveError
)
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError
)

router = APIRouter(prefix="/dishes", tags=["dishes"])


@router.get("", response_model=List[DishResponseSchema], operation_id="getDishes")
async def get_dishes(
        request: Request,
        business_id: Optional[str] = Query(None, description="Filter by business ID")
) -> List[DishResponseSchema]:
    """Retrieve all dishes, optionally filtered by business."""
    dishes = await DishService.get_all_dishes(business_id)
    base_url = str(request.base_url).rstrip('/')

    return [
        DishResponseSchema.from_orm_dish(dish, base_url)
        for dish in dishes
    ]


@router.post("/search", response_model=List[DishResponseSchema], operation_id="searchDishes")
async def search_dishes(
        request: Request,
        search_params: DishSearchSchema
) -> List[DishResponseSchema]:
    """Search dishes by keywords and filters. Designed for AI agent tool calls."""
    dishes = await DishService.search_dishes(
        keywords=search_params.query,
        business_id=search_params.business_id,
        categories=search_params.category,
        cuisines=search_params.cuisine,
        price_max=search_params.price_max,
        is_available=search_params.is_available
    )

    base_url = str(request.base_url).rstrip('/')

    return [
        DishResponseSchema.from_orm_dish(dish, base_url)
        for dish in dishes
    ]


@router.get("/{dish_id}", response_model=DishResponseSchema, operation_id="getDish")
async def get_dish(dish_id: str, request: Request) -> DishResponseSchema:
    """Retrieve a single dish by ID."""
    try:
        dish = await DishService.get_dish_by_id(dish_id)
        base_url = str(request.base_url).rstrip('/')
        return DishResponseSchema.from_orm_dish(dish, base_url)
    except DishNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("", response_model=DishResponseSchema, status_code=status.HTTP_201_CREATED, operation_id="createDish")
async def create_dish(
        dish_data: DishCreateSchema,
        request: Request,
        current_user: User = Depends(get_current_user)
) -> DishResponseSchema:
    """Create a new dish."""
    try:
        dish = await DishService.create_dish(dish_data, current_user)
        base_url = str(request.base_url).rstrip('/')
        return DishResponseSchema.from_orm_dish(dish, base_url)
    except BusinessNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except (InvalidImageError, ImageSaveError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/{dish_id}", response_model=DishResponseSchema, operation_id="updateDish")
async def update_dish(
        dish_id: str,
        dish_data: DishUpdateSchema,
        request: Request,
        current_user: User = Depends(get_current_user)
) -> DishResponseSchema:
    """Update an existing dish."""
    try:
        dish = await DishService.update_dish(dish_id, dish_data, current_user)
        base_url = str(request.base_url).rstrip('/')
        return DishResponseSchema.from_orm_dish(dish, base_url)
    except DishNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except (InvalidImageError, ImageSaveError) as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    

@router.delete("/{dish_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteDish")
async def delete_dish(
        dish_id: str,
        current_user: User = Depends(get_current_user)
) -> None:
    """Delete a dish."""
    try:
        await DishService.delete_dish(dish_id, current_user)
    except DishNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )