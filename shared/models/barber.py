# shared/models/barber.py
from tortoise import Model, fields
from enum import Enum


class AppointmentStatus(str, Enum):
    """Enum for appointment statuses."""
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    COMPLETED = "completed"


class Barber(Model):
    """
    Barber model representing a master/barber in a barbershop.
    """
    id = fields.UUIDField(pk=True)
    business = fields.ForeignKeyField("models.Business", related_name="barbers")
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    specialization = fields.CharField(max_length=255, null=True,
                                      description="e.g. 'Классические стрижки, Борода'")
    image_path = fields.CharField(max_length=500, null=True)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    services: fields.ReverseRelation["BarberService"]
    schedules: fields.ReverseRelation["BarberSchedule"]
    appointments: fields.ReverseRelation["BarberAppointment"]

    class Meta:
        table = "barbers"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} (barber)"


class BarberService(Model):
    """
    Service offered by a barber (e.g. haircut, beard trim).
    """
    id = fields.UUIDField(pk=True)
    barber = fields.ForeignKeyField("models.Barber", related_name="services")
    name = fields.CharField(max_length=255)
    description = fields.TextField(null=True)
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    duration_minutes = fields.IntField(description="Duration of the service in minutes")
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "barber_services"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} — {self.price}₽ ({self.duration_minutes} min)"


class BarberSchedule(Model):
    """
    Weekly schedule for a barber: which days and time slots are available.
    One record = one available time slot on a given weekday.
    """
    id = fields.UUIDField(pk=True)
    barber = fields.ForeignKeyField("models.Barber", related_name="schedules")
    weekday = fields.IntField(
        description="Day of week: 0=Monday, 1=Tuesday, ..., 6=Sunday"
    )
    start_time = fields.TimeField(description="Slot start time (e.g. 10:00)")
    end_time = fields.TimeField(description="Slot end time (e.g. 10:30)")
    is_active = fields.BooleanField(default=True)

    class Meta:
        table = "barber_schedules"
        ordering = ["weekday", "start_time"]

    def __str__(self) -> str:
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        day_name = days[self.weekday] if 0 <= self.weekday <= 6 else str(self.weekday)
        return f"{day_name} {self.start_time}–{self.end_time}"


class BarberAppointment(Model):
    """
    Appointment record: a client books a barber for a specific service at a specific time.
    """
    id = fields.UUIDField(pk=True)
    barber = fields.ForeignKeyField("models.Barber", related_name="appointments")
    service = fields.ForeignKeyField("models.BarberService", related_name="appointments")
    tg_user = fields.ForeignKeyField("models.TGUser", related_name="barber_appointments")
    guest_name = fields.CharField(max_length=255)
    guest_phone = fields.CharField(max_length=20, null=True)
    appointment_date = fields.DateField()
    appointment_time = fields.TimeField()
    status = fields.CharEnumField(AppointmentStatus, default=AppointmentStatus.PENDING)
    notes = fields.TextField(null=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "barber_appointments"
        ordering = ["-appointment_date", "-appointment_time"]

    def __str__(self) -> str:
        return (
            f"Appointment {self.id} — {self.guest_name} "
            f"at {self.appointment_date} {self.appointment_time} [{self.status}]"
        )
