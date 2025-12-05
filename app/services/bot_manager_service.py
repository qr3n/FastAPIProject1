# backend/app/services/bot_manager_service.py
import httpx
import logging
from typing import Optional
from app.core.config import settings
from app.core.redis_ import get_redis

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BotManagerService:
    """Service for managing bot lifecycle through bot-worker."""

    def __init__(self):
        self.bot_worker_url = settings.BOT_WORKER_URL  # http://bot-worker:8080
        self.webhook_base_url = settings.WEBHOOK_BASE_URL  # https://yourdomain.com

    async def register_bot_webhook(self, bot_token: str, business_id: str) -> bool:
        """
        Register webhook for a bot in Telegram.

        Args:
            bot_token: Telegram bot token
            business_id: Business UUID

        Returns:
            True if successful, False otherwise
        """
        webhook_url = f"{self.webhook_base_url}/webhook/{bot_token}"

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Устанавливаем webhook через Telegram API
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/setWebhook",
                    json={
                        "url": webhook_url,
                        "max_connections": 100,
                        "drop_pending_updates": False,
                        "allowed_updates": ["message", "callback_query", "inline_query"]
                    }
                )

                if response.status_code != 200:
                    logger.error(f"Failed to set webhook: {response.text}")
                    return False

                result = response.json()

                if not result.get("ok"):
                    logger.error(f"Telegram API error: {result.get('description')}")
                    return False

                logger.info(f"Webhook registered for business {business_id}")

                # Кэшируем связь токен -> business_id в Redis
                await self._cache_bot_mapping(bot_token, business_id)

                # Уведомляем воркеры о новом боте
                await self._notify_workers_reload()

                return True

        except httpx.TimeoutException:
            logger.error(f"Timeout setting webhook for {business_id}")
            return False
        except Exception as e:
            logger.error(f"Error setting webhook: {e}")
            return False

    async def verify_bot_token(self, bot_token: str) -> Optional[dict]:
        """
        Verify bot token is valid by calling getMe.

        Returns:
            Bot info if valid, None otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getMe"
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        return result.get("result")

                return None

        except Exception as e:
            logger.error(f"Error verifying bot token: {e}")
            return None

    async def unregister_bot_webhook(self, bot_token: str, business_id: str) -> bool:
        """
        Remove webhook for a bot.

        Args:
            bot_token: Telegram bot token
            business_id: Business UUID

        Returns:
            True if successful
        """
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                # Удаляем webhook
                response = await client.post(
                    f"https://api.telegram.org/bot{bot_token}/deleteWebhook",
                    json={"drop_pending_updates": True}
                )

                if response.status_code == 200:
                    logger.info(f"Webhook deleted for business {business_id}")

                    # Удаляем из кэша
                    await self._remove_bot_mapping(bot_token)

                    # Уведомляем воркеры
                    await self._notify_workers_reload()

                    return True

                return False

        except Exception as e:
            logger.error(f"Error deleting webhook: {e}")
            return False

    async def update_bot_token(
            self,
            old_token: str,
            new_token: str,
            business_id: str
    ) -> bool:
        """
        Update bot token (remove old, register new).

        Returns:
            True if successful
        """
        # Удаляем старый webhook
        await self.unregister_bot_webhook(old_token, business_id)

        # Регистрируем новый
        return await self.register_bot_webhook(new_token, business_id)

    async def _cache_bot_mapping(self, bot_token: str, business_id: str):
        """Cache bot token -> business_id mapping in Redis."""
        redis = await get_redis()
        await redis.setex(
            f"bot_token:{bot_token}",
            3600,  # 1 hour TTL
            business_id
        )

    async def _remove_bot_mapping(self, bot_token: str):
        """Remove bot mapping from Redis cache."""
        redis = await get_redis()
        await redis.delete(f"bot_token:{bot_token}")

    async def _notify_workers_reload(self):
        """Notify all workers to reload bot registry via Redis pub/sub."""
        try:
            redis = await get_redis()
            await redis.publish("bot_worker:reload", "reload")
            logger.info("Sent reload notification to workers")
        except Exception as e:
            logger.warning(f"Failed to notify workers: {e}")

    async def get_bot_info(self, bot_token: str) -> Optional[dict]:
        """Get current bot information."""
        return await self.verify_bot_token(bot_token)

    async def get_webhook_info(self, bot_token: str) -> Optional[dict]:
        """
        Get current webhook information for debugging.

        Returns:
            Webhook info or None
        """
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(
                    f"https://api.telegram.org/bot{bot_token}/getWebhookInfo"
                )

                if response.status_code == 200:
                    result = response.json()
                    if result.get("ok"):
                        webhook_info = result.get("result", {})
                        logger.info(
                            f"Webhook info for {bot_token[:10]}...: "
                            f"url={webhook_info.get('url')}, "
                            f"pending_updates={webhook_info.get('pending_update_count')}, "
                            f"last_error={webhook_info.get('last_error_message')}"
                        )
                        return webhook_info

                return None

        except Exception as e:
            logger.error(f"Error getting webhook info: {e}")
            return None

# Singleton instance
bot_manager = BotManagerService()