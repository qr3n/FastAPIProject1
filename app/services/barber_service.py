# app/services/barber_service.py
import base64
import uuid
from datetime import date, time
from decimal import Decimal
from pathlib import Path
from typing import List, Optional
import io

from PIL import Image
from shared.models.barber import Barber, BarberService, BarberSchedule, BarberAppointment, AppointmentStatus
from shared.models.business import Business
from shared.models.tg_user import TGUser
from shared.models.user import User
from app.schemas.barber import (
    BarberCreateSchema,
    BarberUpdateSchema,
    BarberServiceCreateSchema,
    BarberServiceUpdateSchema,
    BarberScheduleCreateSchema,
    AppointmentCreateSchema,
    AppointmentUpdateSchema,
)
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
from app.core.config import settings


class BarberService_:
    """Service for managing barbers, their services, schedules and appointments."""

    # ─── image helpers (same pattern as DishService) ──────────────────

    @staticmethod
    def _decode_base64_image(base64_string: str) -> tuple[bytes, str]:
        try:
            if not base64_string.startswith("data:image/"):
                raise InvalidImageError("Image must be a data URL")

            header, encoded = base64_string.split(",", 1)
            image_format = header.split("/")[1].split(";")[0]

            if image_format not in ["jpeg", "jpg", "png", "webp"]:
                raise InvalidImageError(f"Unsupported image format: {image_format}")

            image_bytes = base64.b64decode(encoded)

            if len(image_bytes) > settings.MAX_UPLOAD_SIZE:
                raise InvalidImageError(
                    f"Image size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE} bytes"
                )

            return image_bytes, image_format

        except Exception as e:
            if isinstance(e, InvalidImageError):
                raise
            raise InvalidImageError(f"Failed to decode image: {str(e)}")

    @staticmethod
    def _save_image_to_disk(image_bytes: bytes, image_format: str) -> str:
        try:
            img = Image.open(io.BytesIO(image_bytes))
            img.verify()
            img = Image.open(io.BytesIO(image_bytes))

            upload_dir = Path(settings.UPLOAD_DIR)
            upload_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{uuid.uuid4()}.{image_format}"
            file_path = upload_dir / filename
            img.save(file_path, format=image_format.upper())

            return filename

        except Exception as e:
            raise ImageSaveError(f"Failed to save image: {str(e)}")

    # ─── Barbers ──────────────────────────────────────────────────────

    @staticmethod
    async def get_barbers(business_id: str) -> List[Barber]:
        """Return all barbers for a business."""
        return await Barber.filter(business_id=business_id).prefetch_related("services").all()

    @staticmethod
    async def get_barber_by_id(barber_id: str) -> Barber:
        barber = await Barber.get_or_none(id=barber_id).prefetch_related("business", "services", "schedules")
        if not barber:
            raise BarberNotFoundError(barber_id)
        return barber

    @staticmethod
    async def create_barber(data: BarberCreateSchema, user: User) -> Barber:
        business = await Business.get_or_none(id=data.business_id)
        if not business:
            raise BusinessNotFoundError(data.business_id)
        if business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        image_filename = None
        if data.image:
            image_bytes, image_format = BarberService_._decode_base64_image(data.image)
            image_filename = BarberService_._save_image_to_disk(image_bytes, image_format)

        return await Barber.create(
            business=business,
            name=data.name,
            description=data.description,
            specialization=data.specialization,
            image_path=image_filename,
            is_active=data.is_active,
        )

    @staticmethod
    async def update_barber(barber_id: str, data: BarberUpdateSchema, user: User) -> Barber:
        barber = await BarberService_.get_barber_by_id(barber_id)
        if barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        update_fields = {}
        if data.name is not None:
            update_fields["name"] = data.name
        if data.description is not None:
            update_fields["description"] = data.description
        if data.specialization is not None:
            update_fields["specialization"] = data.specialization
        if data.is_active is not None:
            update_fields["is_active"] = data.is_active
        if data.image is not None:
            if barber.image_path:
                old = Path(settings.UPLOAD_DIR) / barber.image_path
                if old.exists():
                    old.unlink()
            image_bytes, image_format = BarberService_._decode_base64_image(data.image)
            update_fields["image_path"] = BarberService_._save_image_to_disk(image_bytes, image_format)

        await barber.update_from_dict(update_fields).save()
        await barber.refresh_from_db()
        return barber

    @staticmethod
    async def delete_barber(barber_id: str, user: User) -> None:
        barber = await BarberService_.get_barber_by_id(barber_id)
        if barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()
        if barber.image_path:
            p = Path(settings.UPLOAD_DIR) / barber.image_path
            if p.exists():
                p.unlink()
        await barber.delete()

    # ─── BarberServices (услуги мастера) ─────────────────────────────

    @staticmethod
    async def get_services(barber_id: str) -> List[BarberService]:
        return await BarberService.filter(barber_id=barber_id).all()

    @staticmethod
    async def get_service_by_id(service_id: str) -> BarberService:
        svc = await BarberService.get_or_none(id=service_id).prefetch_related("barber__business")
        if not svc:
            raise BarberServiceNotFoundError(service_id)
        return svc

    @staticmethod
    async def create_service(data: BarberServiceCreateSchema, user: User) -> BarberService:
        barber = await Barber.get_or_none(id=data.barber_id).prefetch_related("business")
        if not barber:
            raise BarberNotFoundError(data.barber_id)
        if barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        return await BarberService.create(
            barber=barber,
            name=data.name,
            description=data.description,
            price=Decimal(data.price),
            duration_minutes=data.duration_minutes,
            is_active=data.is_active,
        )

    @staticmethod
    async def update_service(service_id: str, data: BarberServiceUpdateSchema, user: User) -> BarberService:
        svc = await BarberService_.get_service_by_id(service_id)
        if svc.barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        fields = {}
        if data.name is not None:
            fields["name"] = data.name
        if data.description is not None:
            fields["description"] = data.description
        if data.price is not None:
            fields["price"] = Decimal(data.price)
        if data.duration_minutes is not None:
            fields["duration_minutes"] = data.duration_minutes
        if data.is_active is not None:
            fields["is_active"] = data.is_active

        await svc.update_from_dict(fields).save()
        await svc.refresh_from_db()
        return svc

    @staticmethod
    async def delete_service(service_id: str, user: User) -> None:
        svc = await BarberService_.get_service_by_id(service_id)
        if svc.barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()
        await svc.delete()

    # ─── BarberSchedule ───────────────────────────────────────────────

    @staticmethod
    async def get_schedules(barber_id: str) -> List[BarberSchedule]:
        return await BarberSchedule.filter(barber_id=barber_id, is_active=True).all()

    @staticmethod
    async def create_schedule(data: BarberScheduleCreateSchema, user: User) -> BarberSchedule:
        barber = await Barber.get_or_none(id=data.barber_id).prefetch_related("business")
        if not barber:
            raise BarberNotFoundError(data.barber_id)
        if barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        start_h, start_m = map(int, data.start_time.split(":"))
        end_h, end_m = map(int, data.end_time.split(":"))

        return await BarberSchedule.create(
            barber=barber,
            weekday=data.weekday,
            start_time=time(start_h, start_m),
            end_time=time(end_h, end_m),
            is_active=data.is_active,
        )

    @staticmethod
    async def delete_schedule(schedule_id: str, user: User) -> None:
        slot = await BarberSchedule.get_or_none(id=schedule_id).prefetch_related("barber__business")
        if not slot:
            raise BarberScheduleNotFoundError(schedule_id)
        if slot.barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()
        await slot.delete()

    # ─── Appointments (записи) ────────────────────────────────────────

    @staticmethod
    async def get_appointments(
        business_id: str,
        barber_id: Optional[str] = None,
        appointment_date: Optional[str] = None,
    ) -> List[BarberAppointment]:
        """Get appointments for a business, optionally filtered by barber or date."""
        qs = BarberAppointment.filter(
            barber__business_id=business_id
        ).prefetch_related("barber", "service")

        if barber_id:
            qs = qs.filter(barber_id=barber_id)
        if appointment_date:
            qs = qs.filter(appointment_date=appointment_date)

        return await qs.all()

    @staticmethod
    async def get_appointment_by_id(appointment_id: str) -> BarberAppointment:
        appt = await BarberAppointment.get_or_none(id=appointment_id).prefetch_related(
            "barber__business", "service"
        )
        if not appt:
            raise AppointmentNotFoundError(appointment_id)
        return appt

    @staticmethod
    async def get_user_appointments(tg_user_id: int) -> List[BarberAppointment]:
        """Get all appointments for a Telegram user."""
        return await BarberAppointment.filter(
            tg_user__telegram_id=tg_user_id,
            is_cancelled=False,
        ).prefetch_related("barber", "service").order_by("appointment_date", "appointment_time")

    @staticmethod
    async def _check_slot_free(barber_id: str, appt_date: date, appt_time: time, exclude_id: Optional[str] = None) -> bool:
        """Check that no confirmed/pending appointment overlaps the given slot."""
        qs = BarberAppointment.filter(
            barber_id=barber_id,
            appointment_date=appt_date,
            appointment_time=appt_time,
            status__not_in=[AppointmentStatus.CANCELLED],
        )
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        return not await qs.exists()

    @staticmethod
    async def create_appointment(data: AppointmentCreateSchema) -> BarberAppointment:
        """Create a new appointment (called from TG bot)."""
        barber = await Barber.get_or_none(id=data.barber_id)
        if not barber:
            raise BarberNotFoundError(data.barber_id)

        svc = await BarberService.get_or_none(id=data.service_id)
        if not svc:
            raise BarberServiceNotFoundError(data.service_id)

        tg_user = await TGUser.get_or_none(telegram_id=data.tg_user_id)
        if not tg_user:
            raise BarberNotFoundError(str(data.tg_user_id))  # fallback

        appt_date = date.fromisoformat(data.appointment_date)
        h, m = map(int, data.appointment_time.split(":"))
        appt_time = time(h, m)

        if not await BarberService_._check_slot_free(data.barber_id, appt_date, appt_time):
            raise AppointmentSlotUnavailableError(
                f"Slot {data.appointment_date} {data.appointment_time} is already booked"
            )

        return await BarberAppointment.create(
            barber=barber,
            service=svc,
            tg_user=tg_user,
            guest_name=data.guest_name,
            guest_phone=data.guest_phone,
            appointment_date=appt_date,
            appointment_time=appt_time,
            notes=data.notes,
            status=AppointmentStatus.PENDING,
        )

    @staticmethod
    async def update_appointment(
        appointment_id: str, data: AppointmentUpdateSchema, user: Optional[User] = None
    ) -> BarberAppointment:
        """Update appointment (reschedule / change status). user=None means called by bot."""
        appt = await BarberService_.get_appointment_by_id(appointment_id)

        if user and appt.barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        fields = {}
        if data.appointment_date is not None:
            appt_date = date.fromisoformat(data.appointment_date)
            fields["appointment_date"] = appt_date
        else:
            appt_date = appt.appointment_date

        if data.appointment_time is not None:
            h, m = map(int, data.appointment_time.split(":"))
            appt_time = time(h, m)
            fields["appointment_time"] = appt_time
        else:
            appt_time = appt.appointment_time

        # If date/time changed — check slot availability
        if "appointment_date" in fields or "appointment_time" in fields:
            if not await BarberService_._check_slot_free(
                str(appt.barber_id), appt_date, appt_time, exclude_id=appointment_id
            ):
                raise AppointmentSlotUnavailableError(
                    f"Slot {appt_date} {appt_time} is already booked"
                )

        if data.status is not None:
            fields["status"] = data.status
        if data.notes is not None:
            fields["notes"] = data.notes

        await appt.update_from_dict(fields).save()
        await appt.refresh_from_db()
        return appt

    @staticmethod
    async def cancel_appointment(appointment_id: str, tg_user_id: Optional[int] = None, user: Optional[User] = None) -> BarberAppointment:
        """Cancel an appointment. Can be called by the TG user who booked it, or by admin."""
        appt = await BarberService_.get_appointment_by_id(appointment_id)

        # If called from bot: ensure it belongs to that tg_user
        if tg_user_id and appt.tg_user.telegram_id != tg_user_id:
            raise BarberAccessDeniedError("You can only cancel your own appointments")

        # If called from admin API: ensure business ownership
        if user and appt.barber.business.owner_id != user.id:
            raise BusinessAccessDeniedError()

        appt.status = AppointmentStatus.CANCELLED
        await appt.save()
        return appt

    @staticmethod
    async def get_available_slots(barber_id: str, target_date: str) -> List[str]:
        """
        Return list of available HH:MM slots for a barber on a given date.
        Slots are derived from BarberSchedule for the weekday, minus already booked slots.
        """
        barber = await Barber.get_or_none(id=barber_id)
        if not barber:
            raise BarberNotFoundError(barber_id)

        appt_date = date.fromisoformat(target_date)
        weekday = appt_date.weekday()  # 0=Monday

        schedules = await BarberSchedule.filter(
            barber_id=barber_id,
            weekday=weekday,
            is_active=True,
        ).all()

        if not schedules:
            return []

        # Booked times on this date (non-cancelled)
        booked = await BarberAppointment.filter(
            barber_id=barber_id,
            appointment_date=appt_date,
            status__not_in=[AppointmentStatus.CANCELLED],
        ).values_list("appointment_time", flat=True)

        booked_times = {str(t)[:5] for t in booked}

        available = []
        for slot in schedules:
            slot_str = str(slot.start_time)[:5]
            if slot_str not in booked_times:
                available.append(slot_str)

        return sorted(available)
