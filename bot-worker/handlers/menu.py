# bot-worker/handlers/menu.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from app.models.dish import Dish
import logging

logger = logging.getLogger(__name__)


def register_menu_handlers(router: Router, business_id: str):
    """Register menu-related handlers."""

    @router.message(Command("menu"))
    async def cmd_menu(message: Message):
        """Display business menu."""

        # Получаем блюда из БД с кэшированием
        dishes = await Dish.filter(
            business_id=business_id,
            is_available=True
        ).all()

        if not dishes:
            await message.answer("😔 Меню временно недоступно")
            return

        await message.answer(
            f"🍽 <b>Наше меню</b>\n\n"
            f"Найдено блюд: {len(dishes)}"
        )

        for dish in dishes:
            text = (
                f"<b>{dish.title}</b>\n\n"
                f"{dish.description}\n\n"
                f"💰 {dish.price}₽"
            )

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(
                    text="🛒 В корзину",
                    callback_data=f"add_to_cart:{dish.id}"
                )]
            ])

            try:
                if dish.image_path:
                    await message.answer_photo(
                        photo=f"https://yourdomain.com/uploads/{dish.image_path}",
                        caption=text,
                        reply_markup=keyboard
                    )
                else:
                    await message.answer(text, reply_markup=keyboard)

            except Exception as e:
                logger.error(f"Error sending dish {dish.id}: {e}")

    @router.callback_query(F.data.startswith("add_to_cart:"))
    async def add_to_cart(callback: CallbackQuery):
        """Add dish to cart."""
        dish_id = callback.data.split(":")[1]

        # Логика добавления в корзину (через Redis или БД)
        # ...

        await callback.answer("✅ Добавлено в корзину!", show_alert=True)