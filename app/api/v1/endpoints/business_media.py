# app/api/v1/endpoints/business_media.py
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import List, Optional

from app.schemas.business_media import (
    BusinessMediaCreateSchema,
    BusinessMediaUpdateSchema,
    BusinessMediaResponseSchema,
    MediaReorderSchema
)
from app.services.business_media_service import BusinessMediaService
from app.api.v1.dependencies.auth import get_current_user
from shared.models.user import User
from shared.models.business_media import MediaType
from app.exceptions.business_exceptions import (
    BusinessNotFoundError,
    BusinessAccessDeniedError,
    BusinessMediaNotFoundError
)
from app.exceptions.dish_exceptions import (
    InvalidImageError,
    ImageSaveError
)

router = APIRouter(tags=["business-media"])


@router.post(
    "/businesses/{business_id}/media",
    response_model=BusinessMediaResponseSchema,
    status_code=status.HTTP_201_CREATED,
    operation_id="createBusinessMedia"
)
async def create_business_media(
        business_id: str,
        media_data: BusinessMediaCreateSchema,
        request: Request,
        current_user: User = Depends(get_current_user)
) -> BusinessMediaResponseSchema:
    """
    Upload new media content for a business.
    
    Media types:
    - interior: Interior photos
    - kitchen: Kitchen photos
    - team: Team/staff photos
    - food: General food photos
    - exterior: Exterior/facade photos
    - atmosphere: Atmosphere photos
    - other: Other media
    """
    try:
        media = await BusinessMediaService.create_media(business_id, media_data, current_user)
        base_url = str(request.base_url).rstrip('/')
        return BusinessMediaResponseSchema.from_orm_media(media, base_url)
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


@router.get(
    "/businesses/{business_id}/media",
    response_model=List[BusinessMediaResponseSchema],
    operation_id="getBusinessMedia"
)
async def get_business_media(
        business_id: str,
        request: Request,
        media_type: Optional[MediaType] = Query(None, description="Filter by media type"),
        is_active: Optional[bool] = Query(None, description="Filter by active status")
) -> List[BusinessMediaResponseSchema]:
    """
    Get all media content for a business.
    
    Optionally filter by media type or active status.
    """
    media_list = await BusinessMediaService.get_business_media(
        business_id,
        media_type=media_type,
        is_active=is_active
    )
    base_url = str(request.base_url).rstrip('/')
    return [
        BusinessMediaResponseSchema.from_orm_media(media, base_url)
        for media in media_list
    ]


@router.get(
    "/media/{media_id}",
    response_model=BusinessMediaResponseSchema,
    operation_id="getMediaById"
)
async def get_media_by_id(
        media_id: str,
        request: Request
) -> BusinessMediaResponseSchema:
    """Get a single media item by ID."""
    try:
        media = await BusinessMediaService.get_media_by_id(media_id)
        base_url = str(request.base_url).rstrip('/')
        return BusinessMediaResponseSchema.from_orm_media(media, base_url)
    except BusinessMediaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.put(
    "/media/{media_id}",
    response_model=BusinessMediaResponseSchema,
    operation_id="updateBusinessMedia"
)
async def update_business_media(
        media_id: str,
        media_data: BusinessMediaUpdateSchema,
        request: Request,
        current_user: User = Depends(get_current_user)
) -> BusinessMediaResponseSchema:
    """Update existing media content."""
    try:
        media = await BusinessMediaService.update_media(media_id, media_data, current_user)
        base_url = str(request.base_url).rstrip('/')
        return BusinessMediaResponseSchema.from_orm_media(media, base_url)
    except BusinessMediaNotFoundError as e:
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


@router.delete(
    "/media/{media_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteBusinessMedia"
)
async def delete_business_media(
        media_id: str,
        current_user: User = Depends(get_current_user)
) -> None:
    """Delete a media item."""
    try:
        await BusinessMediaService.delete_media(media_id, current_user)
    except BusinessMediaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessAccessDeniedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )


@router.put(
    "/businesses/{business_id}/media/reorder",
    response_model=List[BusinessMediaResponseSchema],
    operation_id="reorderBusinessMedia"
)
async def reorder_business_media(
        business_id: str,
        reorder_data: MediaReorderSchema,
        request: Request,
        current_user: User = Depends(get_current_user)
) -> List[BusinessMediaResponseSchema]:
    """
    Reorder media items for a business.
    
    Provide a list of media IDs in the desired order.
    """
    try:
        media_list = await BusinessMediaService.reorder_media(
            business_id,
            reorder_data.media_ids,
            current_user
        )
        base_url = str(request.base_url).rstrip('/')
        return [
            BusinessMediaResponseSchema.from_orm_media(media, base_url)
            for media in media_list
        ]
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
    except BusinessMediaNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
