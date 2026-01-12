# app/api/routes/business.py
from fastapi import APIRouter, Depends, Query
from typing import List

from app.api.v1.dependencies.auth import get_current_user
from app.schemas.business import (
    BusinessCreateSchema,
    BusinessUpdateSchema,
    BusinessResponseSchema
)
from app.services.business_service import BusinessService
from shared.models.user import User

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("/", response_model=BusinessResponseSchema, status_code=201)
async def create_business(
        business_data: BusinessCreateSchema,
        current_user: User = Depends(get_current_user)
):
    """
    Create a new business with Telegram bot integration.
    """
    business = await BusinessService.create_business(business_data, current_user)
    return await BusinessResponseSchema.from_orm_business(business)


@router.get("/", response_model=List[BusinessResponseSchema])
async def get_user_businesses(
        include_tables: bool = Query(False, description="Include tables list"),
        include_dishes: bool = Query(False, description="Include dishes list"),
        current_user: User = Depends(get_current_user)
):
    """d
    Get all businesses owned by the current user.

    Query parameters:
    - include_tables: Include full list of tables for each business
    - include_dishes: Include full list of dishes for each business
    """
    businesses = await BusinessService.get_user_businesses(
        current_user,
        include_tables=include_tables,
        include_dishes=include_dishes
    )

    return [
        await BusinessResponseSchema.from_orm_business(
            business,
            include_tables=include_tables,
            include_dishes=include_dishes
        )
        for business in businesses
    ]


@router.get("/{business_id}", response_model=BusinessResponseSchema)
async def get_business(
        business_id: str,
        include_tables: bool = Query(False, description="Include tables list"),
        include_dishes: bool = Query(False, description="Include dishes list"),
        current_user: User = Depends(get_current_user)
):
    """
    Get a specific business by ID.

    Query parameters:
    - include_tables: Include full list of tables
    - include_dishes: Include full list of dishes
    """
    business = await BusinessService.get_business_by_id(
        business_id,
        include_tables=include_tables,
        include_dishes=include_dishes
    )
    BusinessService.verify_business_access(business, current_user)

    return await BusinessResponseSchema.from_orm_business(
        business,
        include_tables=include_tables,
        include_dishes=include_dishes
    )


@router.put("/{business_id}", response_model=BusinessResponseSchema)
async def update_business(
        business_id: str,
        business_data: BusinessUpdateSchema,
        current_user: User = Depends(get_current_user)
):
    """
    Update a business.
    """
    business = await BusinessService.update_business(
        business_id,
        business_data,
        current_user
    )
    return await BusinessResponseSchema.from_orm_business(business)


@router.delete("/{business_id}", status_code=204)
async def delete_business(
        business_id: str,
        current_user: User = Depends(get_current_user)
):
    """
    Delete a business and unregister its bot.
    """
    await BusinessService.delete_business(business_id, current_user)


@router.get("/{business_id}/bot-status")
async def get_bot_status(
        business_id: str,
        current_user: User = Depends(get_current_user)
):
    """
    Get current bot status and information.
    """
    return await BusinessService.get_bot_status(business_id, current_user)


@router.get("/{business_id}/stats")
async def get_business_stats(
        business_id: str,
        current_user: User = Depends(get_current_user)
):
    """
    Get business statistics including tables and dishes counts.

    Returns:
    - Total and active tables count
    - Available tables count
    - Total and available dishes count
    """
    return await BusinessService.get_business_stats(business_id, current_user)