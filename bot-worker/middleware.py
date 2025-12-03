# bot-worker/middleware.py
from typing import Callable, Dict, Any, Awaitable
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Update, Message, CallbackQuery
from app.models.business import Business
import logging

logger = logging.getLogger(__name__)


class BusinessContextMiddleware(BaseMiddleware):
    """
    Middleware that adds business context to all handlers.

    Adds business_id and business object to handler data,
    making it available in all handlers without manual fetching.
    """

    def __init__(self, business_id: str):
        """
        Initialize middleware with business ID.

        Args:
            business_id: UUID of the business this bot belongs to
        """
        super().__init__()
        self.business_id = business_id
        self._business_cache = None

    async def __call__(
            self,
            handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
            event: TelegramObject,
            data: Dict[str, Any]
    ) -> Any:
        """
        Process update and inject business context.

        Args:
            handler: Next handler in chain
            event: Telegram event (Message, CallbackQuery, etc.)
            data: Handler data dictionary

        Returns:
            Handler result
        """
        # Добавляем business_id в данные
        data["business_id"] = self.business_id

        # Загружаем бизнес из БД (с кэшированием)
        if self._business_cache is None:
            try:
                self._business_cache = await Business.get_or_none(id=self.business_id)

                if self._business_cache is None:
                    logger.error(f"Business {self.business_id} not found")
                    # Отправляем сообщение пользователю
                    if isinstance(event, (Message, CallbackQuery)):
                        await self._send_error_message(event)
                    return

            except Exception as e:
                logger.error(f"Error loading business {self.business_id}: {e}")
                if isinstance(event, (Message, CallbackQuery)):
                    await self._send_error_message(event)
                return

        # Добавляем бизнес в данные
        data["business"] = self._business_cache

        # Добавляем user_id из события
        user_id = None
        if isinstance(event, Message):
            user_id = event.from_user.id
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id

        data["telegram_user_id"] = user_id

        # Логируем для отладки
        logger.debug(
            f"Processing update for business {self.business_id} "
            f"from user {user_id}"
        )

        # Вызываем следующий handler
        return await handler(event, data)

    async def _send_error_message(self, event):
        """Send error message to user."""
        text = "⚠️ Произошла ошибка. Пожалуйста, попробуйте позже."

        try:
            if isinstance(event, Message):
                await event.answer(text)
            elif isinstance(event, CallbackQuery):
                await event.message.answer(text)
        except Exception as e:
            logger.error(f"Failed to send error message: {e}")