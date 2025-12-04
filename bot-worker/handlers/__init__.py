# bot-worker/handlers/__init__.py
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from .menu import register_menu_handlers


def register_handlers(dp, business_id: str):
    """Register all handlers for a bot."""

    # Главный роутер
    main_router = Router()

    @main_router.message(Command("start"))
    async def cmd_start(message: Message):
        await message.answer(
            "👋 Добро пожаловать!\n\n"
            "🍽 /menu - Посмотреть меню\n"
            "📋 /orders - Мои заказы\n"
            "ℹ️ /help - Помощь"
        )

    register_menu_handlers(main_router, business_id)

    dp.include_router(main_router)