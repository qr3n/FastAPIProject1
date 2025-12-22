# app/services/table_service.py
from shared.models.table import Table, TableBooking, TableStatus
from app.schemas.table import TableCreateSchema, TableUpdateSchema, TableBookingCreateSchema, BulkTablesSchema
from shared.models.tg_user import TGUser
from shared.models.user import User
from app.exceptions.business_exceptions import BusinessNotFoundError, BusinessAccessDeniedError
from fastapi import HTTPException, status
from datetime import date, time, datetime, timedelta
from typing import List, Optional


class TableService:
    """Service for managing restaurant tables and bookings."""

    @staticmethod
    async def create_table(business_id: str, table_data: TableCreateSchema, current_user: User) -> Table:
        """Create a new table."""
        from shared.models.business import Business

        business = await Business.get_or_none(id=business_id)
        if not business:
            raise BusinessNotFoundError(f"Business {business_id} not found")

        if business.owner_id != current_user.id:
            raise BusinessAccessDeniedError("You don't have access to this business")

        existing_table = await Table.get_or_none(
            business_id=business_id,
            table_number=table_data.table_number
        )
        if existing_table:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table {table_data.table_number} already exists"
            )

        table = await Table.create(
            business_id=business_id,
            table_number=table_data.table_number,
            capacity=table_data.capacity
        )
        return table

    @staticmethod
    async def get_business_tables(business_id: str) -> List[Table]:
        """Get all tables for a business."""
        from shared.models.business import Business

        business = await Business.get_or_none(id=business_id)
        if not business:
            raise BusinessNotFoundError(f"Business {business_id} not found")

        tables = await Table.filter(business_id=business_id, is_active=True)
        return tables

    @staticmethod
    async def get_table(table_id: str, current_user: User) -> Table:
        """Get table by ID with access verification."""
        from shared.models.business import Business

        table = await Table.get_or_none(id=table_id).prefetch_related("business")
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )

        if table.business.owner_id != current_user.id:
            raise BusinessAccessDeniedError("You don't have access to this table")

        return table

    @staticmethod
    async def update_table(table_id: str, table_data: TableUpdateSchema, current_user: User) -> Table:
        """Update a table."""
        table = await TableService.get_table(table_id, current_user)

        update_data = table_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(table, field, value)

        await table.save()
        return table

    @staticmethod
    async def delete_table(table_id: str, current_user: User) -> None:
        """Delete a table (soft delete)."""
        table = await TableService.get_table(table_id, current_user)
        table.is_active = False
        await table.save()

    @staticmethod
    async def book_table(
        table_id: str,
        booking_data: TableBookingCreateSchema
    ) -> TableBooking:
        """Book a table."""
        table = await Table.get_or_none(id=table_id)
        if not table:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Table not found"
            )

        # Verify table capacity
        if booking_data.num_guests > table.capacity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Table capacity is {table.capacity}, cannot book for {booking_data.num_guests} guests"
            )

        # Get or create TGUser
        tg_user = await TGUser.get_or_none(telegram_id=booking_data.telegram_id)
        if not tg_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Telegram user {booking_data.telegram_id} not found"
            )

        # Check for overlapping bookings
        booking_start = datetime.combine(booking_data.booking_date, booking_data.booking_time)
        booking_end = booking_start + timedelta(minutes=booking_data.duration_minutes)

        overlapping = await TableBooking.filter(
            table_id=table_id,
            is_cancelled=False,
            booking_date=booking_data.booking_date
        ).prefetch_related("table")

        for booking in overlapping:
            existing_start = datetime.combine(booking.booking_date, booking.booking_time)
            existing_end = existing_start + timedelta(minutes=booking.duration_minutes)

            if not (booking_end <= existing_start or booking_start >= existing_end):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Table is already booked for this time"
                )

        booking = await TableBooking.create(
            table_id=table_id,
            tg_user_id=tg_user.id,
            guest_name=booking_data.guest_name,
            guest_phone=booking_data.guest_phone,
            num_guests=booking_data.num_guests,
            booking_date=booking_data.booking_date,
            booking_time=booking_data.booking_time,
            duration_minutes=booking_data.duration_minutes,
            notes=booking_data.notes
        )

        # Update table status
        table.status = TableStatus.BOOKED
        await table.save()

        return booking

    @staticmethod
    async def cancel_booking(booking_id: str, current_user: User) -> TableBooking:
        """Cancel a booking."""
        booking = await TableBooking.get_or_none(id=booking_id).prefetch_related("table__business")
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )

        if booking.table.business.owner_id != current_user.id:
            raise BusinessAccessDeniedError("You don't have access to this booking")

        if booking.is_cancelled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Booking is already cancelled"
            )

        booking.is_cancelled = True
        await booking.save()

        # Check if there are other active bookings for the table
        active_bookings = await TableBooking.filter(
            table_id=booking.table_id,
            is_cancelled=False
        ).exists()

        if not active_bookings:
            booking.table.status = TableStatus.AVAILABLE
            await booking.table.save()

        return booking

    @staticmethod
    async def get_table_bookings(table_id: str, current_user: User) -> List[TableBooking]:
        """Get all bookings for a table."""
        table = await TableService.get_table(table_id, current_user)
        bookings = await TableBooking.filter(table_id=table_id).prefetch_related("tg_user")
        return bookings

    @staticmethod
    async def bulk_update_tables(
            business_id: str,
            bulk_data: BulkTablesSchema,
            current_user: User
    ) -> dict:
        """
        Bulk create/update/delete tables for a business.
        Logic:
        - If total_tables > current tables: create new tables
        - If total_tables < current tables: delete tables without bookings (soft delete)
        - Update capacity for all existing tables
        """
        from shared.models.business import Business

        business = await Business.get_or_none(id=business_id)
        if not business:
            raise BusinessNotFoundError(f"Business {business_id} not found")

        if business.owner_id != current_user.id:
            raise BusinessAccessDeniedError("You don't have access to this business")

        # Get existing active tables
        existing_tables = await Table.filter(
            business_id=business_id,
            is_active=True
        ).order_by('table_number')

        current_count = len(existing_tables)
        target_count = bulk_data.total_tables

        created_count = 0
        updated_count = 0
        deleted_count = 0

        # Case 1: Need to create more tables
        if target_count > current_count:
            # Update existing tables capacity
            for table in existing_tables:
                if table.capacity != bulk_data.default_capacity:
                    table.capacity = bulk_data.default_capacity
                    await table.save()
                    updated_count += 1

            # Find the highest table number
            max_table_number = max([t.table_number for t in existing_tables]) if existing_tables else 0

            # Create new tables
            tables_to_create = target_count - current_count
            for i in range(tables_to_create):
                await Table.create(
                    business_id=business_id,
                    table_number=max_table_number + i + 1,
                    capacity=bulk_data.default_capacity
                )
                created_count += 1

        # Case 2: Need to delete tables
        elif target_count < current_count:
            tables_to_keep = target_count
            tables_to_delete = current_count - target_count

            # Update tables we're keeping
            for table in existing_tables[:tables_to_keep]:
                if table.capacity != bulk_data.default_capacity:
                    table.capacity = bulk_data.default_capacity
                    await table.save()
                    updated_count += 1

            # Check which tables can be deleted (no active bookings)
            for table in existing_tables[tables_to_keep:]:
                # Check if table has active bookings
                has_active_bookings = await TableBooking.filter(
                    table_id=table.id,
                    is_cancelled=False,
                    booking_date__gte=date.today()
                ).exists()

                if has_active_bookings:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Cannot delete table {table.table_number}: has active bookings. Please cancel bookings first."
                    )

                # Soft delete
                table.is_active = False
                await table.save()
                deleted_count += 1

        # Case 3: Same count, just update capacity
        else:
            for table in existing_tables:
                if table.capacity != bulk_data.default_capacity:
                    table.capacity = bulk_data.default_capacity
                    await table.save()
                    updated_count += 1

        # Get final state of tables
        final_tables = await Table.filter(
            business_id=business_id,
            is_active=True
        ).order_by('table_number')

        return {
            'created': created_count,
            'updated': updated_count,
            'deleted': deleted_count,
            'total': len(final_tables),
            'tables': final_tables
        }