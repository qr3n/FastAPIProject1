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
from app.models.user import User
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError
)

router = APIRouter(prefix="/businesses", tags=["businesses"])


@router.post("/", response_model=BusinessResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_business(
        business_data: BusinessCreateSchema,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """
    Create a new business with Telegram bot.

    Args:
        business_data: Business creation data
        current_user: Current authenticated user

    Returns:
        Created business data
    """
    business = await BusinessService.create_business(business_data, current_user)
    return BusinessResponseSchema.from_orm_business(business)


@router.get("/", response_model=List[BusinessResponseSchema])
async def get_user_businesses(
        current_user: User = Depends(get_current_user)
) -> List[BusinessResponseSchema]:
    """
    Get all businesses owned by current user.

    Args:
        current_user: Current authenticated user

    Returns:
        List of user's businesses
    """
    businesses = await BusinessService.get_user_businesses(current_user)
    return [BusinessResponseSchema.from_orm_business(b) for b in businesses]


@router.get("/{business_id}", response_model=BusinessResponseSchema)
async def get_business(
        business_id: str,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """
    Get business by ID.

    Args:
        business_id: Business UUID
        current_user: Current authenticated user

    Returns:
        Business data

    Raises:
        HTTPException: 404 if business not found, 403 if access denied
    """
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


@router.put("/{business_id}", response_model=BusinessResponseSchema)
async def update_business(
        business_id: str,
        business_data: BusinessUpdateSchema,
        current_user: User = Depends(get_current_user)
) -> BusinessResponseSchema:
    """
    Update a business.

    Args:
        business_id: Business UUID
        business_data: Updated business data
        current_user: Current authenticated user

    Returns:
        Updated business data

    Raises:
        HTTPException: 404 if business not found, 403 if access denied
    """
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


@router.delete("/{business_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_business(
        business_id: str,
        current_user: User = Depends(get_current_user)
) -> None:
    """
    Delete a business.

    Args:
        business_id: Business UUID
        current_user: Current authenticated user

    Raises:
        HTTPException: 404 if business not found, 403 if access denied
    """
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