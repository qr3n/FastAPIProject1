"""
Callback webhook routes for receiving AI agent responses.
"""
from aiohttp import web
from aiogram import Bot
from shared.models.tg_user import TGUser
import logging
import json

logger = logging.getLogger(__name__)


async def ai_callback_handler(request: web.Request) -> web.Response:
    """
    Handle callback from Make.com AI agent.

    Expected payload:
    {
        "status": "ok",
        "user_id": "123456789",
        "trace_id": "uuid",
        "result_text": "AI response text",
        "url": "https://photo.url",  # optional
        "weight": "200g",  # optional
        "price": "650"  # optional
    }
    """
    try:
        data = await request.json()

        user_id = data.get("user_id")
        trace_id = data.get("trace_id")
        result_text = data.get("result_text")
        photo_url = data.get("url")

        if not user_id or not result_text:
            logger.error(f"Invalid callback payload: {data}")
            return web.json_response(
                {"error": "Missing required fields"},
                status=400
            )

        logger.info(f"Received AI callback: user={user_id}, trace={trace_id}")

        # Check if user exists
        user = await TGUser.get_or_none(telegram_id=int(user_id))
        if not user:
            logger.error(f"User not found: {user_id}")
            return web.json_response(
                {"error": "User not found"},
                status=404
            )

        # Get bot instance from request app
        bot_registry = request.app['bot_registry']

        # Find the bot for this user's business
        # (Simplified: assumes business_id is stored or can be derived)
        # You may need to adjust this based on your architecture
        bot_data = await bot_registry.get_bot_for_user(user_id)

        if not bot_data:
            logger.error(f"Bot not found for user: {user_id}")
            return web.json_response(
                {"error": "Bot not found"},
                status=404
            )

        bot = bot_data['bot']

        # Send response to user
        try:
            if photo_url:
                # Send with photo
                await bot.send_photo(
                    chat_id=int(user_id),
                    photo=photo_url,
                    caption=result_text,
                    parse_mode="HTML"
                )
            else:
                # Send text only
                await bot.send_message(
                    chat_id=int(user_id),
                    text=result_text,
                    parse_mode="HTML"
                )

            logger.info(f"Successfully sent response to user: {user_id}")

        except Exception as e:
            logger.error(f"Error sending message to user {user_id}: {e}")
            return web.json_response(
                {"error": "Failed to send message"},
                status=500
            )

        return web.json_response({
            "status": "success",
            "user_id": user_id,
            "trace_id": trace_id
        })

    except json.JSONDecodeError:
        logger.error("Invalid JSON in callback")
        return web.json_response(
            {"error": "Invalid JSON"},
            status=400
        )

    except Exception as e:
        logger.error(f"Error processing callback: {e}", exc_info=True)
        return web.json_response(
            {"error": "Internal server error"},
            status=500
        )


async def health_check_callback(request: web.Request) -> web.Response:
    """Health check endpoint for callback service."""
    return web.json_response({
        "status": "healthy",
        "service": "ai_callback"
    })