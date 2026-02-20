# app/api/v1/endpoints/barbers.py
from fastapi import APIRouter, HTTPException, status, Request, Depends, Query
from typing import List, Optional

from app.schemas.barber import (
    BarberCreateSchema,
    BarberUpdateSchema,
    BarberResponseSchema,
    BarberServiceCreateSchema,
    BarberServiceUpdateSchema,
    BarberServiceResponseSchema,
    BarberScheduleCreateSchema,
    BarberScheduleResponseSchema,
    AppointmentCreateSchema,
    AppointmentUpdateSchema,
    AppointmentResponseSchema,
)
from app.services.barber_service import BarberService_
from app.api.v1.dependencies.auth import get_current_user
from shared.models.user import User
from app.exceptions.barber_exceptions import (
    BarberNotFoundError,
    BarberServiceNotFoundError,
    BarberScheduleNotFoundError,
    AppointmentNotFoundError,
    AppointmentSlotUnavailableError,
    BarberAccessDeniedError,
)
from app.exceptions.business_exceptions import BusinessNotFoundError, BusinessAccessDeniedError
from app.exceptions.dish_exceptions import InvalidImageError, ImageSaveError

router = APIRouter(prefix="/barbers", tags=["barbers"])


# ─────────────────────────── Barbers ───────────────────────────

@router.get("", response_model=List[BarberResponseSchema], operation_id="getBarbers")
async def get_barbers(
    request: Request,
    business_id: str = Query(..., description="Business UUID"),
) -> List[BarberResponseSchema]:
    """Get all barbers (masters) for a barbershop."""
    barbers = await BarberService_.get_barbers(business_id)
    base_url = str(request.base_url).rstrip("/")
    return [BarberResponseSchema.from_orm_barber(b, base_url) for b in barbers]


@router.get("/{barber_id}", response_model=BarberResponseSchema, operation_id="getBarber")
async def get_barber(barber_id: str, request: Request) -> BarberResponseSchema:
    """Get a single barber by ID."""
    try:
        barber = await BarberService_.get_barber_by_id(barber_id)
        base_url = str(request.base_url).rstrip("/")
        return BarberResponseSchema.from_orm_barber(barber, base_url)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.post("", response_model=BarberResponseSchema, status_code=status.HTTP_201_CREATED, operation_id="createBarber")
async def create_barber(
    data: BarberCreateSchema,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> BarberResponseSchema:
    """Create a new barber (master) in a barbershop. Requires authentication."""
    try:
        barber = await BarberService_.create_barber(data, current_user)
        base_url = str(request.base_url).rstrip("/")
        return BarberResponseSchema.from_orm_barber(barber, base_url)
    except BusinessNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidImageError, ImageSaveError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put("/{barber_id}", response_model=BarberResponseSchema, operation_id="updateBarber")
async def update_barber(
    barber_id: str,
    data: BarberUpdateSchema,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> BarberResponseSchema:
    """Update a barber."""
    try:
        barber = await BarberService_.update_barber(barber_id, data, current_user)
        base_url = str(request.base_url).rstrip("/")
        return BarberResponseSchema.from_orm_barber(barber, base_url)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except (InvalidImageError, ImageSaveError) as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete("/{barber_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteBarber")
async def delete_barber(
    barber_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a barber."""
    try:
        await BarberService_.delete_barber(barber_id, current_user)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─────────────────────────── Services (услуги) ───────────────────────────

@router.get("/{barber_id}/services", response_model=List[BarberServiceResponseSchema], operation_id="getBarberServices")
async def get_barber_services(barber_id: str) -> List[BarberServiceResponseSchema]:
    """Get all services offered by a barber."""
    services = await BarberService_.get_services(barber_id)
    return [BarberServiceResponseSchema.from_orm(s) for s in services]


@router.post("/services", response_model=BarberServiceResponseSchema, status_code=status.HTTP_201_CREATED, operation_id="createBarberService")
async def create_barber_service(
    data: BarberServiceCreateSchema,
    current_user: User = Depends(get_current_user),
) -> BarberServiceResponseSchema:
    """Create a new service for a barber."""
    try:
        svc = await BarberService_.create_service(data, current_user)
        return BarberServiceResponseSchema.from_orm(svc)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.put("/services/{service_id}", response_model=BarberServiceResponseSchema, operation_id="updateBarberService")
async def update_barber_service(
    service_id: str,
    data: BarberServiceUpdateSchema,
    current_user: User = Depends(get_current_user),
) -> BarberServiceResponseSchema:
    """Update a barber service."""
    try:
        svc = await BarberService_.update_service(service_id, data, current_user)
        return BarberServiceResponseSchema.from_orm(svc)
    except BarberServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/services/{service_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteBarberService")
async def delete_barber_service(
    service_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a barber service."""
    try:
        await BarberService_.delete_service(service_id, current_user)
    except BarberServiceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─────────────────────────── Schedules (расписание) ───────────────────────────

@router.get("/{barber_id}/schedules", response_model=List[BarberScheduleResponseSchema], operation_id="getBarberSchedules")
async def get_barber_schedules(barber_id: str) -> List[BarberScheduleResponseSchema]:
    """Get active schedule slots for a barber."""
    slots = await BarberService_.get_schedules(barber_id)
    return [BarberScheduleResponseSchema.from_orm(s) for s in slots]


@router.post("/schedules", response_model=BarberScheduleResponseSchema, status_code=status.HTTP_201_CREATED, operation_id="createBarberSchedule")
async def create_barber_schedule(
    data: BarberScheduleCreateSchema,
    current_user: User = Depends(get_current_user),
) -> BarberScheduleResponseSchema:
    """Create a schedule slot for a barber."""
    try:
        slot = await BarberService_.create_schedule(data, current_user)
        return BarberScheduleResponseSchema.from_orm(slot)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.delete("/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT, operation_id="deleteBarberSchedule")
async def delete_barber_schedule(
    schedule_id: str,
    current_user: User = Depends(get_current_user),
) -> None:
    """Delete a schedule slot."""
    try:
        await BarberService_.delete_schedule(schedule_id, current_user)
    except BarberScheduleNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


# ─────────────────────────── Available slots ───────────────────────────

@router.get("/{barber_id}/available-slots", response_model=List[str], operation_id="getAvailableSlots")
async def get_available_slots(
    barber_id: str,
    date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="YYYY-MM-DD"),
) -> List[str]:
    """Get available time slots for a barber on a specific date."""
    try:
        return await BarberService_.get_available_slots(barber_id, date)
    except BarberNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# ─────────────────────────── Appointments (записи) ───────────────────────────

@router.get("/appointments", response_model=List[AppointmentResponseSchema], operation_id="getAppointments")
async def get_appointments(
    business_id: str = Query(..., description="Business UUID"),
    barber_id: Optional[str] = Query(None),
    date: Optional[str] = Query(None, pattern=r"^\d{4}-\d{2}-\d{2}$"),
    current_user: User = Depends(get_current_user),
) -> List[AppointmentResponseSchema]:
    """Get appointments for a barbershop (admin view)."""
    appts = await BarberService_.get_appointments(business_id, barber_id, date)
    return [AppointmentResponseSchema.from_orm(a) for a in appts]


@router.post("/appointments", response_model=AppointmentResponseSchema, status_code=status.HTTP_201_CREATED, operation_id="createAppointment")
async def create_appointment(data: AppointmentCreateSchema) -> AppointmentResponseSchema:
    """Create a new appointment. Called by the Telegram bot (no auth required)."""
    try:
        appt = await BarberService_.create_appointment(data)
        return AppointmentResponseSchema.from_orm(appt)
    except (BarberNotFoundError, BarberServiceNotFoundError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AppointmentSlotUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("/appointments/{appointment_id}", response_model=AppointmentResponseSchema, operation_id="getAppointment")
async def get_appointment(appointment_id: str) -> AppointmentResponseSchema:
    """Get a single appointment by ID."""
    try:
        appt = await BarberService_.get_appointment_by_id(appointment_id)
        return AppointmentResponseSchema.from_orm(appt)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.put("/appointments/{appointment_id}", response_model=AppointmentResponseSchema, operation_id="updateAppointment")
async def update_appointment(
    appointment_id: str,
    data: AppointmentUpdateSchema,
    current_user: User = Depends(get_current_user),
) -> AppointmentResponseSchema:
    """Update (reschedule / change status) an appointment. Admin only."""
    try:
        appt = await BarberService_.update_appointment(appointment_id, data, user=current_user)
        return AppointmentResponseSchema.from_orm(appt)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except AppointmentSlotUnavailableError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except BusinessAccessDeniedError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))


@router.post("/appointments/{appointment_id}/cancel", response_model=AppointmentResponseSchema, operation_id="cancelAppointment")
async def cancel_appointment(
    appointment_id: str,
    tg_user_id: Optional[int] = Query(None, description="Telegram user ID (if called from bot)"),
    current_user: Optional[User] = Depends(get_current_user),
) -> AppointmentResponseSchema:
    """Cancel an appointment. Can be called by admin or by the TG bot user."""
    try:
        appt = await BarberService_.cancel_appointment(
            appointment_id, tg_user_id=tg_user_id, user=current_user
        )
        return AppointmentResponseSchema.from_orm(appt)
    except AppointmentNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except (BarberAccessDeniedError, BusinessAccessDeniedError) as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
