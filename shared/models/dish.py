# app/models/dish.py
from tortoise import Model, fields


class Dish(Model):
    """
    Dish database model representing a menu item for a business.
    """

    id = fields.UUIDField(pk=True)
    business = fields.ForeignKeyField("models.Business", related_name="dishes")
    title = fields.CharField(max_length=100, index=True)
    description = fields.TextField()
    price = fields.DecimalField(max_digits=10, decimal_places=2)
    image_path = fields.CharField(max_length=500)
    is_available = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "dishes"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} - {self.price}₽"