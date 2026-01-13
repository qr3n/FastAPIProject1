# bot-worker/handlers/callback.py
from aiohttp import web
from shared.models.tg_user import TGUser
import logging
import os
import json  # Добавьте этот импорт!

logger = logging.getLogger(__name__)

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "your-secret-key")


async def ai_callback_handler(request: web.Request) -> web.Response:
    """
    Handle callbacks from AI assistant.

    Expected payload:
    {
        "thread_id": "thread_123456789_1234567890",
        "business_id": "uuid-of-business",
        "message": "{\"result_text\": \"...\", \"image_url\": \"...\"}",
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
        business_id = data.get('business_id')
        message = data.get('message')

        if not thread_id or not message or not business_id:
            return web.Response(status=400, text="Missing required fields")

        # 🔧 ИСПРАВЛЕНИЕ: Парсим message, если это строка
        if isinstance(message, str):
            try:
                message = json.loads(message)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in message field: {e}")
                return web.Response(status=400, text="Invalid message JSON")

        message_text = message.get('result_text')
        image_url = message.get('url')  # или 'image_url', в зависимости от вашего формата

        if not message_text:
            return web.Response(status=400, text="Missing result_text")

        # Находим пользователя по thread_id
        user = await TGUser.filter(thread_id=thread_id).first()

        if not user:
            logger.error(f"User not found for thread_id: {thread_id}")
            return web.Response(status=404, text="User not found")

        # Получаем бота через business_id
        bot_registry = request.app['bot_registry']
        bot_data = await bot_registry.get_bot_by_business(business_id)

        if not bot_data:
            logger.error(f"Bot not found for business_id: {business_id}")
            return web.Response(status=404, text="Bot not found")

        bot = bot_data['bot']

        # Отправляем сообщение пользователю
        if image_url and image_url.strip():
            try:
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=image_url,
                    caption=message_text,
                    parse_mode="Markdown"
                )
                logger.info(f"✅ AI response with image delivered to user {user.telegram_id}")
            except Exception as img_error:
                logger.error(f"Error sending image: {img_error}", exc_info=True)
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=message_text,
                    parse_mode="Markdown"
                )
                logger.info(f"✅ AI response (text only) delivered to user {user.telegram_id}")
        else:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message_text,
                parse_mode="Markdown"
            )
            logger.info(f"✅ AI response delivered to user {user.telegram_id}")

        logger.info(f"Message delivered via business {business_id}")

        return web.json_response({"status": "ok"})

    except Exception as e:
        logger.error(f"Error in AI callback handler: {e}", exc_info=True)
        return web.Response(status=500, text="Internal server error")