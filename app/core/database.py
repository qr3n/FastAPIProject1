# app/core/database.py
from tortoise import Tortoise
from app.core.config import settings


def get_db_url() -> str:
    """
    Convert DATABASE_URL to Tortoise-ORM compatible format.
    Tortoise-ORM uses 'postgres://' instead of 'postgresql://'
    """
    db_url = settings.DATABASE_URL
    if db_url.startswith("postgresql://"):
        return db_url.replace("postgresql://", "postgres://", 1)
    return db_url


TORTOISE_ORM = {
    "connections": {
        "default": get_db_url()
    },
    "apps": {
        "models": {
            "models": [
                "shared.models.user",
                "shared.models.business",
                "shared.models.dish",
                "aerich.models"
            ],
            "default_connection": "default",
        }
    },
}


async def init_db() -> None:
    """
    Initialize database connection.
    """
    await Tortoise.init(config=TORTOISE_ORM)
    await Tortoise.generate_schemas()


async def close_db() -> None:
    """
    Close database connection.
    """
    await Tortoise.close_connections()