# app/api/v1/endpoints/tables.py
from fastapi import APIRouter, Depends, status, HTTPException
from typing import List

from app.schemas.table import (
    TableCreateSchema,
    TableUpdateSchema,
    TableResponseSchema,
    TableBookingCreateSchema,
    TableBookingResponseSchema, BulkTablesResponseSchema, BulkTablesSchema
)
from app.services.table_service import TableService
from app.api.v1.dependencies.auth import get_current_user
from shared.models.user import User
from app.exceptions.business_exceptions import BusinessAccessDeniedError, BusinessNotFoundError

router = APIRouter(prefix="/businesses/{business_id}/tables", tags=["tables"])


@router.post("", response_model=TableResponseSchema, status_code=status.HTTP_201_CREATED)
async def create_table(
    business_id: str,
    table_data: TableCreateSchema,
    current_user: User = Depends(get_current_user)
) -> TableResponseSchema:
    """Create a new table for a business."""
    try:
        table = await TableService.create_table(business_id, table_data, current_user)
        return TableResponseSchema.from_orm_table(table)
    except (BusinessNotFoundError, BusinessAccessDeniedError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, BusinessAccessDeniedError) else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("", response_model=List[TableResponseSchema])
async def get_tables(
    business_id: str,
    current_user: User = Depends(get_current_user)
) -> List[TableResponseSchema]:
    """Get all tables for a business."""
    try:
        tables = await TableService.get_business_tables(business_id, current_user)
        return [TableResponseSchema.from_orm_table(t) for t in tables]
    except (BusinessNotFoundError, BusinessAccessDeniedError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e, BusinessAccessDeniedError) else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/{table_id}", response_model=TableResponseSchema)
async def get_table(
    business_id: str,
    table_id: str,
    current_user: User = Depends(get_current_user)
) -> TableResponseSchema:
    """Get a specific table."""
    try:
        table = await TableService.get_table(table_id, current_user)
        return TableResponseSchema.from_orm_table(table)
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/{table_id}", response_model=TableResponseSchema)
async def update_table(
    business_id: str,
    table_id: str,
    table_data: TableUpdateSchema,
    current_user: User = Depends(get_current_user)
) -> TableResponseSchema:
    """Update a table."""
    try:
        table = await TableService.update_table(table_id, table_data, current_user)
        return TableResponseSchema.from_orm_table(table)
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{table_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_table(
    business_id: str,
    table_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """Delete a table (soft delete)."""
    try:
        await TableService.delete_table(table_id, current_user)
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/{table_id}/bookings", response_model=TableBookingResponseSchema, status_code=status.HTTP_201_CREATED)
async def book_table(
    business_id: str,
    table_id: str,
    booking_data: TableBookingCreateSchema
) -> TableBookingResponseSchema:
    """Book a table (public endpoint)."""
    booking = await TableService.book_table(table_id, booking_data)
    return TableBookingResponseSchema.from_orm_booking(booking)


@router.get("/{table_id}/bookings", response_model=List[TableBookingResponseSchema])
async def get_table_bookings(
    business_id: str,
    table_id: str,
    current_user: User = Depends(get_current_user)
) -> List[TableBookingResponseSchema]:
    """Get all bookings for a table."""
    try:
        bookings = await TableService.get_table_bookings(table_id, current_user)
        return [TableBookingResponseSchema.from_orm_booking(b) for b in bookings]
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/{table_id}/bookings/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_booking(
    business_id: str,
    table_id: str,
    booking_id: str,
    current_user: User = Depends(get_current_user)
) -> None:
    """Cancel a booking."""
    try:
        await TableService.cancel_booking(booking_id, current_user)
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/bulk", response_model=BulkTablesResponseSchema)
async def bulk_update_tables(
        business_id: str,
        bulk_data: BulkTablesSchema,
        current_user: User = Depends(get_current_user)
) -> BulkTablesResponseSchema:
    """
    Bulk create/update/delete tables for a business.

    - Creates new tables if total_tables > current count
    - Deletes tables (soft delete) if total_tables < current count (only if no active bookings)
    - Updates capacity for all tables
    """
    try:
        result = await TableService.bulk_update_tables(business_id, bulk_data, current_user)
        return BulkTablesResponseSchema(
            created=result['created'],
            updated=result['updated'],
            deleted=result['deleted'],
            total=result['total'],
            tables=[TableResponseSchema.from_orm_table(t) for t in result['tables']]
        )
    except (BusinessNotFoundError, BusinessAccessDeniedError) as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN if isinstance(e,
                                                                BusinessAccessDeniedError) else status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )