# bot-worker/handlers/callback.py
from aiohttp import web
from aiogram import Bot
from shared.models.tg_user import TGUser
import logging
import os

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret-key")


async def ai_callback_handler(request: web.Request) -> web.Response:
    """
    Handle callbacks from AI assistant.

    Expected payload:
    {
        "thread_id": "thread_123456789_1234567890",
        "message": "Ответ от AI ассистента",
        "secret": "your-secret-key"
    }
    """
    try:
        data = await request.json()

        # Проверяем секретный ключ
        if data.get('secret') != WEBHOOK_SECRET:
            logger.warning("Invalid webhook secret")
            return web.Response(status=403, text="Forbidden")

        thread_id = data.get('thread_id')
        message_text = data.get('message')

        if not thread_id or not message_text:
            return web.Response(status=400, text="Missing required fields")

        # Находим пользователя по thread_id
        user = await TGUser.filter(thread_id=thread_id).first()

        if not user:
            logger.error(f"User not found for thread_id: {thread_id}")
            return web.Response(status=404, text="User not found")

        # Получаем бота из реестра
        bot_registry = request.app['bot_registry']

        # Находим бота для этого пользователя
        # Предполагаем, что bot_token передается в payload или извлекается из контекста
        bot_token = data.get('bot_token')

        if not bot_token:
            # Если токен не передан, можно попробовать найти его через business_id
            logger.error("Bot token not provided in callback")
            return web.Response(status=400, text="Bot token required")

        bot_data = await bot_registry.get_bot(bot_token)

        if not bot_data:
            logger.error(f"Bot not found for token: {bot_token[:10]}...")
            return web.Response(status=404, text="Bot not found")

        bot = bot_data['bot']

        # Отправляем сообщение пользователю
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message_text,
            parse_mode="HTML"
        )

        logger.info(f"AI response delivered to user {user.telegram_id}")

        return web.json_response({"status": "ok"})

    except Exception as e:
        logger.error(f"Error in AI callback handler: {e}", exc_info=True)
        return web.Response(status=500, text="Internal server error")