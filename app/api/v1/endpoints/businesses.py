# app/api/v1/endpoints/businesses.py
from fastapi import APIRouter, HTTPException, status, Depends
from typing import List

from app.schemas.business import (
    BusinessCreateSchema,
    BusinessUpdateSchema,
    BusinessResponseSchema
)
from app.services.business_service import BusinessService
from app.api.v1.dependencies.auth import get_current_user
from shared.models.user import User
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("", response_model=BusinessResponseSchema, status_code=status.HTTP_201_CREATED)  # ← изменено
async def create_business(
        business_data: BusinessCreateSchema,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """Create a new business with Telegram bot."""
    business = await BusinessService.create_business(business_data, current_user)
    return BusinessResponseSchema.from_orm_business(business)


@router.get("", response_model=List[BusinessResponseSchema])  # ← изменено
async def get_user_businesses(
        current_user: User = Depends(get_current_user)
) -> List[BusinessResponseSchema]:
    """Get all businesses owned by current user."""
    businesses = await BusinessService.get_user_businesses(current_user)
    return [BusinessResponseSchema.from_orm_business(b) for b in businesses]


@router.get("/{business_id}", response_model=BusinessResponseSchema)  # ← без изменений
async def get_business(
        business_id: str,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """Get business by ID."""
    try:
        business = await BusinessService.get_business_by_id(business_id)
        BusinessService.verify_business_access(business, current_user)
        return BusinessResponseSchema.from_orm_business(business)
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


@router.put("/{business_id}", response_model=BusinessResponseSchema)  # ← без изменений
async def update_business(
        business_id: str,
        business_data: BusinessUpdateSchema,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """Update a business."""
    try:
        business = await BusinessService.update_business(
            business_id,
            business_data,
            current_user
        )
        return BusinessResponseSchema.from_orm_business(business)
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


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)  # ← без изменений
async def delete_business(
        business_id: str,
        current_user: User = Depends(get_current_user)
) -> None:
    """Delete a business."""
    try:
        await BusinessService.delete_business(business_id, current_user)
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