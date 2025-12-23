from tortoise import Model, fields
from enum import Enum
from datetime import datetime


class TableStatus(str, Enum):
    """Enum for table statuses."""
    AVAILABLE = "available"
    BOOKED = "booked"
    OCCUPIED = "occupied"


# shared/models/table.py
class Table(Model):
    """
    Table model representing a restaurant table.
    """
    id = fields.UUIDField(pk=True)
    business = fields.ForeignKeyField("models.Business", related_name="tables")
    table_number = fields.IntField()
    capacity = fields.IntField()  # Number of seats
    floor = fields.IntField(default=1)  # Floor number (can be negative)
    status = fields.CharEnumField(TableStatus, default=TableStatus.AVAILABLE)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    bookings: fields.ReverseRelation["TableBooking"]

    class Meta:
        table = "tables"
        ordering = ["floor", "table_number"]  # Сортировка по этажу, затем по номеру
        unique_together = (("business", "table_number"),)

    def __str__(self) -> str:
        return f"Table {self.table_number}, Floor {self.floor} (Capacity: {self.capacity})"


class TableBooking(Model):
    """
    Table booking model for restaurant reservations.
    """
    id = fields.UUIDField(pk=True)
    table = fields.ForeignKeyField("models.Table", related_name="table_bookings")
    tg_user = fields.ForeignKeyField("models.TGUser", related_name="bookings")
    guest_name = fields.CharField(max_length=255)
    guest_phone = fields.CharField(max_length=20, null=True)
    num_guests = fields.IntField()
    booking_date = fields.DateField()
    booking_time = fields.TimeField()
    duration_minutes = fields.IntField(default=120)
    notes = fields.TextField(null=True)
    is_cancelled = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "table_bookings"
        ordering = ["-booking_date", "-booking_time"]

    def __str__(self) -> str:
        return f"Booking {self.id} - {self.guest_name} at {self.booking_date} {self.booking_time}"

