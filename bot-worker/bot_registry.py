"""
Bot Registry - manages multiple bot instances with caching.
Fixed version with proper reload and duplicate handling.
"""
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from shared.models.business import Business
from middleware import BusinessContextMiddleware
from handlers.menu import register_menu_handlers
from handlers.ai_assistant import register_ai_handlers
import redis.asyncio as redis
import logging
import json

logger = logging.getLogger(__name__)


class BotRegistry:
    """Registry for managing multiple bot instances."""

    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.bots = {}  # {bot_token: {bot, dispatcher, business_id}}

    async def load_active_bots(self):
        """Load all active bots from database."""
        businesses = await Business.filter(
            telegram_bot_token__not_isnull=True,
            is_active=True
        ).all()

        logger.info(f"Found {len(businesses)} active businesses with bots")

        # Группируем бизнесы по токенам для обнаружения дубликатов
        token_to_businesses = {}
        for business in businesses:
            token = business.telegram_bot_token
            if token not in token_to_businesses:
                token_to_businesses[token] = []
            token_to_businesses[token].append(business)

        # Регистрируем ботов
        for token, business_list in token_to_businesses.items():
            if len(business_list) > 1:
                logger.warning(
                    f"⚠️ Token {token[:10]}... used by {len(business_list)} businesses: "
                    f"{[b.name for b in business_list]}"
                )
                # Используем первый бизнес или самый новый
                business = max(business_list, key=lambda b: b.created_at)
                logger.warning(f"Using business: {business.name} (id: {business.id})")
            else:
                business = business_list[0]

            await self.register_bot(business)

    async def register_bot(self, business: Business):
        """Register a bot instance."""
        token = business.telegram_bot_token

        if not token:
            logger.warning(f"No bot token for business {business.id}")
            return

        # Проверяем, не зарегистрирован ли уже этот токен
        if token in self.bots:
            existing_business_id = self.bots[token]['business_id']
            if existing_business_id != str(business.id):
                logger.warning(
                    f"Token already registered for business {existing_business_id}, "
                    f"skipping {business.id}"
                )
            else:
                logger.info(f"Bot already registered: {business.name}")
            return

        try:
            # Create bot and dispatcher
            bot = Bot(
                token=token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            # Важно: создаем НОВЫЙ диспетчер для каждого бота
            dp = Dispatcher()

            # Register middleware
            dp.message.middleware(BusinessContextMiddleware(str(business.id)))
            dp.callback_query.middleware(BusinessContextMiddleware(str(business.id)))

            # Создаем роутер для хендлеров
            router = Router()

            # Register handlers в роутер
            register_menu_handlers(router, str(business.id))
            register_ai_handlers(router, str(business.id))

            # Включаем роутер в диспетчер
            dp.include_router(router)

            # Store in registry
            self.bots[token] = {
                'bot': bot,
                'dispatcher': dp,
                'business_id': str(business.id),
                'business_name': business.name
            }

            # Cache in Redis for quick lookup
            await self.redis.setex(
                f"bot:{token}",
                3600,  # 1 hour TTL
                json.dumps({
                    'business_id': str(business.id),
                    'business_name': business.name
                })
            )

            # Create reverse mapping: business_id -> token
            await self.redis.setex(
                f"business_bot:{business.id}",
                3600,
                token
            )

            logger.info(
                f"✅ Registered bot for {business.name} "
                f"(business_id: {business.id})"
            )

        except Exception as e:
            logger.error(f"Failed to register bot for {business.name}: {e}", exc_info=True)

    async def get_bot(self, bot_token: str):
        """Get bot instance by token."""
        if bot_token in self.bots:
            return self.bots[bot_token]

        # Try loading from Redis cache
        cached = await self.redis.get(f"bot:{bot_token}")
        if cached:
            data = json.loads(cached)
            business = await Business.get_or_none(id=data['business_id'])
            if business and business.is_active:
                await self.register_bot(business)
                return self.bots.get(bot_token)

        return None

    async def get_bot_for_user(self, user_id: str):
        """Get bot instance for a specific user."""
        # Check Redis for last used bot
        cached_token = await self.redis.get(f"user_bot:{user_id}")
        if cached_token:
            return await self.get_bot(cached_token)

        # Default to first available bot (for single-bot setup)
        if self.bots:
            return list(self.bots.values())[0]

        return None

    async def get_bot_by_business(self, business_id: str):
        """Get bot instance by business ID."""
        token = await self.redis.get(f"business_bot:{business_id}")
        if token:
            return await self.get_bot(token)

        # Fallback: search in loaded bots
        for bot_data in self.bots.values():
            if bot_data['business_id'] == business_id:
                return bot_data

        return None

    async def reload_all_bots(self):
        """Reload all bots from database."""
        logger.info("🔄 Starting bot registry reload...")

        # Закрываем все существующие боты
        await self.close_all()

        # Очищаем реестр
        self.bots.clear()

        # Очищаем Redis кэш
        await self._clear_redis_cache()

        # Загружаем ботов заново
        await self.load_active_bots()

        logger.info(f"✅ Reload complete. Active bots: {len(self.bots)}")

    async def _clear_redis_cache(self):
        """Clear bot-related Redis cache."""
        try:
            # Удаляем все ключи bot:*
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match="bot:*",
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break

            # Удаляем все ключи business_bot:*
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(
                    cursor=cursor,
                    match="business_bot:*",
                    count=100
                )
                if keys:
                    await self.redis.delete(*keys)
                if cursor == 0:
                    break

            logger.info("✅ Redis cache cleared")
        except Exception as e:
            logger.error(f"Error clearing Redis cache: {e}")

    async def close_all(self):
        """Close all bot sessions."""
        for token, bot_data in list(self.bots.items()):
            try:
                await bot_data['bot'].session.close()
                logger.info(f"Closed bot session for {bot_data['business_name']}")
            except Exception as e:
                logger.error(f"Error closing bot session: {e}")

    async def get_bots_count(self) -> int:
        """Get number of registered bots."""
        return len(self.bots)

    async def unregister_bot(self, bot_token: str):
        """
        Unregister a specific bot.

        Args:
            bot_token: Token of bot to unregister
        """
        if bot_token not in self.bots:
            logger.warning(f"Bot {bot_token[:10]}... not found in registry")
            return

        bot_data = self.bots[bot_token]

        try:
            # Закрываем сессию
            await bot_data['bot'].session.close()

            # Удаляем из реестра
            del self.bots[bot_token]

            # Удаляем из Redis
            await self.redis.delete(f"bot:{bot_token}")
            await self.redis.delete(f"business_bot:{bot_data['business_id']}")

            logger.info(f"✅ Unregistered bot for {bot_data['business_name']}")

        except Exception as e:
            logger.error(f"Error unregistering bot: {e}")