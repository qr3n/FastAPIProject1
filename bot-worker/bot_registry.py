# bot-worker/bot_registry.py
import logging
from typing import Dict, Optional
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
import redis.asyncio as redis

from shared.models.business import Business
from handlers import register_handlers
from middleware import BusinessContextMiddleware

logger = logging.getLogger(__name__)


class BotRegistry:
    """
    Registry for managing multiple bot instances with Redis caching.
    Supports thousands of bots efficiently.
    """

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.bots: Dict[str, dict] = {}
        self.storage = RedisStorage(redis_client)

    async def get_bot(self, bot_token: str) -> Optional[dict]:
        """
        Get bot instance by token with caching.
        Returns: {bot, dispatcher, business_id}
        """
        # Проверяем in-memory кэш
        if bot_token in self.bots:
            return self.bots[bot_token]

        # Проверяем Redis кэш
        business_id = await self.redis.get(f"bot_token:{bot_token}")

        if not business_id:
            # Загружаем из БД
            business = await Business.filter(
                telegram_bot_token=bot_token,
                is_active=True
            ).first()

            if not business:
                return None

            business_id = str(business.id)

            # Кэшируем в Redis (TTL 1 час)
            await self.redis.setex(
                f"bot_token:{bot_token}",
                3600,
                business_id
            )

        # Создаем бота если его нет в памяти
        if bot_token not in self.bots:
            await self._create_bot_instance(bot_token, business_id)

        return self.bots.get(bot_token)

    async def _create_bot_instance(self, bot_token: str, business_id: str):
        """Create new bot instance."""
        try:
            bot = Bot(
                token=bot_token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            dp = Dispatcher(storage=self.storage)

            dp.update.middleware(BusinessContextMiddleware(business_id))

            # Регистрируем handlers
            register_handlers(dp, business_id)

            self.bots[bot_token] = {
                'bot': bot,
                'dispatcher': dp,
                'business_id': business_id
            }

            logger.info(f"Bot instance created for business {business_id}")

        except Exception as e:
            logger.error(f"Failed to create bot instance: {e}")
            raise

    async def load_active_bots(self):
        """
        Pre-load active bots from database.
        For 1000+ bots, this might be done lazily.
        """
        businesses = await Business.filter(is_active=True).limit(100)  # Лимит для начального прогрева

        for business in businesses:
            await self._create_bot_instance(
                business.telegram_bot_token,
                str(business.id)
            )

        logger.info(f"Pre-loaded {len(businesses)} bots")

    async def reload_all_bots(self):
        """Reload all bots (clear cache)."""
        # Закрываем текущие сессии
        for bot_data in self.bots.values():
            await bot_data['bot'].session.close()

        self.bots.clear()

        # Очищаем Redis кэш
        keys = await self.redis.keys("bot_token:*")
        if keys:
            await self.redis.delete(*keys)

        # Перезагружаем
        await self.load_active_bots()

        logger.info("All bots reloaded")

    async def get_bots_count(self) -> int:
        """Get number of loaded bots."""
        return len(self.bots)

    async def close_all(self):
        """Close all bot sessions."""
        for bot_data in self.bots.values():
            await bot_data['bot'].session.close()

        logger.info("All bot sessions closed")