# bot-worker/handlers/__init__.py
from aiogram import Router
from .menu import register_menu_handlers
from .ai_assistant import register_ai_handlers


def register_handlers(dp, business_id: str):
    """Register all handlers for a bot instance."""
    router = Router()

    register_menu_handlers(router, business_id)
    register_ai_handlers(router, business_id)

    dp.include_router(router)


def register_callback_handlers(app):
    """Register HTTP callback handlers for AI assistant responses."""
    from .callback import ai_callback_handler
    app.router.add_post('/ai-callback', ai_callback_handler)
    app.router.add_post('/ai-callback/', ai_callback_handler)
