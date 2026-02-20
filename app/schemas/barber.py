# app/schemas/barber.py
from pydantic import BaseModel, Field, field_validator
from decimal import Decimal
from typing import Optional, List
from shared.models.barber import AppointmentStatus


# ─────────────────────────── Barber ───────────────────────────

class BarberCreateSchema(BaseModel):
    """Schema for creating a new barber (master)."""

    business_id: str = Field(..., description="Business UUID")
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    specialization: Optional[str] = Field(None, max_length=255)
    image: Optional[str] = Field(None, description="Base64 encoded image")
    is_active: bool = True

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not value.startswith("data:image/"):
            raise ValueError("Image must be a valid base64 data URL")
        return value


class BarberUpdateSchema(BaseModel):
    """Schema for updating a barber."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    specialization: Optional[str] = Field(None, max_length=255)
    image: Optional[str] = Field(None, description="Base64 encoded image")
    is_active: Optional[bool] = None

    @field_validator("image")
    @classmethod
    def validate_image(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        if not value.startswith("data:image/"):
            raise ValueError("Image must be a valid base64 data URL")
        return value


class BarberResponseSchema(BaseModel):
    """Schema for barber responses."""

    id: str
    business_id: str
    name: str
    description: Optional[str]
    specialization: Optional[str]
    image: Optional[str]
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm_barber(cls, barber: "Barber", base_url: str) -> "BarberResponseSchema":
        return cls(
            id=str(barber.id),
            business_id=str(barber.business_id),
            name=barber.name,
            description=barber.description,
            specialization=barber.specialization,
            image=f"{base_url}/uploads/{barber.image_path}" if barber.image_path else None,
            is_active=barber.is_active,
            created_at=barber.created_at.isoformat(),
            updated_at=barber.updated_at.isoformat(),
        )


# ─────────────────────────── BarberService ───────────────────────────

class BarberServiceCreateSchema(BaseModel):
    """Schema for creating a service offered by a barber."""

    barber_id: str = Field(..., description="Barber UUID")
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: str = Field(..., pattern=r"^\d+(\.\d{1,2})?$")
    duration_minutes: int = Field(..., gt=0, le=480)
    is_active: bool = True

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: str) -> str:
        price_decimal = Decimal(value)
        if price_decimal <= 0:
            raise ValueError("Price must be positive")
        if price_decimal > Decimal("9999999.99"):
            raise ValueError("Price is too large")
        return value


class BarberServiceUpdateSchema(BaseModel):
    """Schema for updating a barber service."""

    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[str] = Field(None, pattern=r"^\d+(\.\d{1,2})?$")
    duration_minutes: Optional[int] = Field(None, gt=0, le=480)
    is_active: Optional[bool] = None

    @field_validator("price")
    @classmethod
    def validate_price(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        price_decimal = Decimal(value)
        if price_decimal <= 0:
            raise ValueError("Price must be positive")
        if price_decimal > Decimal("9999999.99"):
            raise ValueError("Price is too large")
        return value


class BarberServiceResponseSchema(BaseModel):
    """Schema for barber service responses."""

    id: str
    barber_id: str
    name: str
    description: Optional[str]
    price: str
    duration_minutes: int
    is_active: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, svc: "BarberService") -> "BarberServiceResponseSchema":
        return cls(
            id=str(svc.id),
            barber_id=str(svc.barber_id),
            name=svc.name,
            description=svc.description,
            price=str(svc.price),
            duration_minutes=svc.duration_minutes,
            is_active=svc.is_active,
            created_at=svc.created_at.isoformat(),
            updated_at=svc.updated_at.isoformat(),
        )


# ─────────────────────────── BarberSchedule ───────────────────────────

class BarberScheduleCreateSchema(BaseModel):
    """Schema for creating a schedule slot for a barber."""

    barber_id: str = Field(..., description="Barber UUID")
    weekday: int = Field(..., ge=0, le=6, description="0=Mon … 6=Sun")
    start_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    end_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    is_active: bool = True

    @field_validator("end_time")
    @classmethod
    def end_after_start(cls, end: str, info) -> str:
        start = info.data.get("start_time")
        if start and end <= start:
            raise ValueError("end_time must be after start_time")
        return end


class BarberScheduleResponseSchema(BaseModel):
    """Schema for barber schedule responses."""

    id: str
    barber_id: str
    weekday: int
    start_time: str
    end_time: str
    is_active: bool

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, slot: "BarberSchedule") -> "BarberScheduleResponseSchema":
        return cls(
            id=str(slot.id),
            barber_id=str(slot.barber_id),
            weekday=slot.weekday,
            start_time=str(slot.start_time)[:5],
            end_time=str(slot.end_time)[:5],
            is_active=slot.is_active,
        )


# ─────────────────────────── BarberAppointment ───────────────────────────

class AppointmentCreateSchema(BaseModel):
    """Schema for creating an appointment (used by the TG bot)."""

    barber_id: str = Field(..., description="Barber UUID")
    service_id: str = Field(..., description="BarberService UUID")
    tg_user_id: int = Field(..., description="Telegram user ID")
    guest_name: str = Field(..., min_length=2, max_length=255)
    guest_phone: Optional[str] = Field(None, max_length=20)
    appointment_date: str = Field(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD")
    appointment_time: str = Field(..., pattern=r"^\d{2}:\d{2}$", description="HH:MM")
    notes: Optional[str] = Field(None, max_length=1000)


class AppointmentUpdateSchema(BaseModel):
    """Schema for updating an appointment."""

    appointment_date: Optional[str] = Field(None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    appointment_time: Optional[str] = Field(None, pattern=r"^\d{2}:\d{2}$")
    status: Optional[AppointmentStatus] = None
    notes: Optional[str] = Field(None, max_length=1000)


class AppointmentResponseSchema(BaseModel):
    """Schema for appointment responses."""

    id: str
    barber_id: str
    barber_name: str
    service_id: str
    service_name: str
    guest_name: str
    guest_phone: Optional[str]
    appointment_date: str
    appointment_time: str
    status: str
    notes: Optional[str]
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}

    @classmethod
    def from_orm(cls, appt: "BarberAppointment") -> "AppointmentResponseSchema":
        return cls(
            id=str(appt.id),
            barber_id=str(appt.barber_id),
            barber_name=appt.barber.name if hasattr(appt, "barber") else "",
            service_id=str(appt.service_id),
            service_name=appt.service.name if hasattr(appt, "service") else "",
            guest_name=appt.guest_name,
            guest_phone=appt.guest_phone,
            appointment_date=str(appt.appointment_date),
            appointment_time=str(appt.appointment_time)[:5],
            status=appt.status.value,
            notes=appt.notes,
            created_at=appt.created_at.isoformat(),
            updated_at=appt.updated_at.isoformat(),
        )
