# app/schemas/table.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, time
from enum import Enum


class TableStatusEnum(str, Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    OCCUPIED = "occupied"


class TableCreateSchema(BaseModel):
    table_number: int = Field(..., gt=0)
    capacity: int = Field(..., gt=0)


class TableUpdateSchema(BaseModel):
    table_number: Optional[int] = Field(None, gt=0)
    capacity: Optional[int] = Field(None, gt=0)
    status: Optional[TableStatusEnum] = None
    is_active: Optional[bool] = None


class TableResponseSchema(BaseModel):
    id: str
    table_number: int
    capacity: int
    status: str
    is_active: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_table(cls, table):
        return cls(
            id=str(table.id),
            table_number=table.table_number,
            capacity=table.capacity,
            status=table.status,
            is_active=table.is_active,
            created_at=table.created_at.isoformat(),
            updated_at=table.updated_at.isoformat()
        )


class TableBookingCreateSchema(BaseModel):
    telegram_id: int
    guest_name: str = Field(..., min_length=1, max_length=255)
    guest_phone: Optional[str] = Field(None, max_length=20)
    num_guests: int = Field(..., gt=0)
    booking_date: date
    booking_time: time
    duration_minutes: int = Field(default=120, gt=0)
    notes: Optional[str] = None


class TableBookingResponseSchema(BaseModel):
    id: str
    table_id: str
    telegram_id: int
    guest_name: str
    guest_phone: Optional[str]
    num_guests: int
    booking_date: str
    booking_time: str
    duration_minutes: int
    notes: Optional[str]
    is_cancelled: bool
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_booking(cls, booking):
        return cls(
            id=str(booking.id),
            table_id=str(booking.table_id),
            telegram_id=booking.tg_user.telegram_id,
            guest_name=booking.guest_name,
            guest_phone=booking.guest_phone,
            num_guests=booking.num_guests,
            booking_date=booking.booking_date.isoformat(),
            booking_time=booking.booking_time.isoformat(),
            duration_minutes=booking.duration_minutes,
            notes=booking.notes,
            is_cancelled=booking.is_cancelled,
            created_at=booking.created_at.isoformat(),
            updated_at=booking.updated_at.isoformat()
        )
