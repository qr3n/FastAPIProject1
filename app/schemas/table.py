# app/schemas/table.py
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import date, time, datetime, timedelta
from enum import Enum


class TableStatusEnum(str, Enum):
    AVAILABLE = "available"
    BOOKED = "booked"
    OCCUPIED = "occupied"






class TableCreateSchema(BaseModel):
    table_number: int = Field(..., gt=0)
    capacity: int = Field(..., gt=0)
    floor: int = Field(default=1)  # По умолчанию 1 этаж


class TableUpdateSchema(BaseModel):
    table_number: Optional[int] = Field(None, gt=0)
    capacity: Optional[int] = Field(None, gt=0)
    status: Optional[TableStatusEnum] = None
    is_active: Optional[bool] = None
    floor: Optional[int] = None  # Можно обновить этаж


class BookingInfoSchema(BaseModel):
    """Nested schema for booking information in table response."""
    booking_id: str
    guest_name: str
    guest_phone: Optional[str]
    num_guests: int
    booking_date: str
    booking_time: str
    duration_minutes: int
    notes: Optional[str]
    telegram_id: int
    is_cancelled: bool
    created_at: str


class TableResponseSchema(BaseModel):
    id: str
    table_number: int
    capacity: int
    status: str
    is_active: bool
    created_at: str
    updated_at: str
    floor: int  # Добавляем этаж в ответ
    current_booking: Optional[BookingInfoSchema] = None  # Текущее активное бронирование
    upcoming_bookings: List[BookingInfoSchema] = []  # Все будущие бронирования

    class Config:
        from_attributes = True

    @classmethod
    def from_orm_table(cls, table):
        current_booking = None
        upcoming_bookings = []
        
        # Проверяем, есть ли загруженные бронирования
        # Используем try-except для безопасной проверки
        try:
            if hasattr(table, 'table_bookings'):
                # Проверяем, были ли фактически загружены данные
                bookings = table.table_bookings
                
                # Если это ReverseRelation, который не был prefetched, просто пропускаем
                if bookings and hasattr(bookings, '_fetched') and not bookings._fetched:
                    # Данные не загружены, пропускаем
                    pass
                else:
                    from datetime import datetime
                    
                    now = datetime.now()
                    
                    # Обрабатываем все активные бронирования
                    for booking in bookings:
                        if booking.is_cancelled:
                            continue
                        
                        # Получаем telegram_id безопасно
                        telegram_id = 0
                        if hasattr(booking, 'tg_user'):
                            try:
                                telegram_id = booking.tg_user.telegram_id
                            except:
                                telegram_id = 0
                        
                        # Создаем объект бронирования
                        booking_info = BookingInfoSchema(
                            booking_id=str(booking.id),
                            guest_name=booking.guest_name,
                            guest_phone=booking.guest_phone,
                            num_guests=booking.num_guests,
                            booking_date=booking.booking_date.isoformat(),
                            booking_time=booking.booking_time.isoformat(),
                            duration_minutes=booking.duration_minutes,
                            notes=booking.notes,
                            telegram_id=telegram_id,
                            is_cancelled=booking.is_cancelled,
                            created_at=booking.created_at.isoformat()
                        )
                        
                        # Определяем, текущее это бронирование или будущее
                        booking_datetime = datetime.combine(booking.booking_date, booking.booking_time)
                        booking_end = booking_datetime + timedelta(minutes=booking.duration_minutes)
                        
                        # Текущее бронирование - если оно сейчас активно
                        if booking_datetime <= now <= booking_end:
                            current_booking = booking_info
                        # Будущее бронирование
                        elif booking_datetime > now:
                            upcoming_bookings.append(booking_info)
        except Exception:
            # Если произошла ошибка при доступе к бронированиям, просто пропускаем
            # Это может произойти, если связь не была prefetched
            pass
        
        return cls(
            id=str(table.id),
            table_number=table.table_number,
            capacity=table.capacity,
            status=table.status,
            is_active=table.is_active,
            created_at=table.created_at.isoformat(),
            updated_at=table.updated_at.isoformat(),
            floor=table.floor,  # Добавляем этаж
            current_booking=current_booking,
            upcoming_bookings=upcoming_bookings
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

class BulkTablesSchema(BaseModel):
    """Schema for bulk table creation/update."""
    total_tables: int = Field(..., gt=0, le=100)
    default_capacity: int = Field(..., gt=0, le=20)
    default_floor: int = Field(default=1)

    @validator('total_tables')
    def validate_total_tables(cls, v):
        if v > 100:
            raise ValueError('Cannot create more than 100 tables at once')
        return v


class BulkTablesResponseSchema(BaseModel):
    """Response schema for bulk table operations."""
    created: int
    updated: int
    deleted: int
    total: int
    tables: List[TableResponseSchema]
