# bot-worker/handlers/__init__.py
from aiogram import Router
from .menu import register_menu_handlers
from .ai_assistant import register_ai_handlers
from .barbershop import register_barbershop_handlers


def register_handlers(dp, business_id: str, business_type: str = "restaurant"):
    """Register all handlers for a bot instance based on business type."""
    from shared.models.business import BusinessType

    router = Router()

    if business_type == BusinessType.BARBERSHOP:
        register_barbershop_handlers(router, business_id)
    else:
        register_menu_handlers(router, business_id)
        register_ai_handlers(router, business_id)

    dp.include_router(router)


def register_callback_handlers(app):
    """Register HTTP callback handlers for AI assistant responses."""
    from .callback import ai_callback_handler
    app.router.add_post('/ai-callback', ai_callback_handler)
    app.router.add_post('/ai-callback/', ai_callback_handler)
