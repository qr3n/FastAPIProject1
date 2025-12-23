# bot-worker/handlers/ai_assistant.py
from aiogram import Router, F
from aiogram.types import Message

from shared.models.business import Business
from shared.models.tg_user import TGUser
from datetime import datetime
import logging
import aiohttp
import os

logger = logging.getLogger(__name__)

AI_ASSISTANT_URL = "https://hook.eu2.make.com/hnukd8a6uo6lghmhkl6pdyl30crsztnu"


def register_ai_handlers(router: Router, business_id: str):
    """Register AI assistant handlers."""

    @router.message(F.text)
    async def handle_text_message(message: Message):
        """Handle any text message from user."""
        try:
            # Получаем или создаем пользователя
            user = await TGUser.filter(telegram_id=message.from_user.id).first()
            business = await Business.filter(id=business_id).first()

            if not user:
                # Создаем нового пользователя
                user = await TGUser.create(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name,
                    language_code=message.from_user.language_code or "ru",
                    last_interaction=datetime.utcnow()
                )
                logger.info(f"Created new user: {user.telegram_id}")
            else:
                # Обновляем время последнего взаимодействия
                user.last_interaction = datetime.utcnow()
                await user.save()

            # Генерируем thread_id если его нет
            if not user.thread_id:
                user.thread_id = f"thread_{user.telegram_id}_{int(datetime.utcnow().timestamp())}"
                await user.save()

            # Отправляем typing indicator
            await message.bot.send_chat_action(
                chat_id=message.chat.id,
                action="typing"
            )

            # Отправляем сообщение к AI-ассистенту
            async with aiohttp.ClientSession() as session:
                payload = {
                    "thread_id": user.thread_id,
                    "user_id": user.telegram_id,
                    "business_id": business_id,
                    "message": message.text,
                    "business_name": business.name,
                    "business_description": business.description,
                    "user_data": {
                        "username": user.username,
                        "first_name": user.first_name,
                        "last_name": user.last_name,
                        "language_code": user.language_code
                    }
                }

                async with session.post(AI_ASSISTANT_URL, json=payload) as resp:
                    if resp.status == 200:
                        logger.info(f"Message sent to AI assistant for user {user.telegram_id}")
                    else:
                        error_text = await resp.text()
                        logger.error(f"AI assistant error: {resp.status} - {error_text}")
                        await message.answer(
                            "😔 Произошла ошибка при обработке сообщения. Попробуйте позже."
                        )

        except Exception as e:
            logger.error(f"Error handling text message: {e}", exc_info=True)
            await message.answer(
                "😔 Произошла ошибка. Пожалуйста, попробуйте еще раз."
            )