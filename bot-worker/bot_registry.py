"""
Bot Registry - manages multiple bot instances with caching.
Updated with user-to-bot mapping support.
"""
from aiogram import Bot, Dispatcher
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

        for business in businesses:
            await self.register_bot(business)

    async def register_bot(self, business: Business):
        """Register a bot instance."""
        token = business.telegram_bot_token

        if not token:
            logger.warning(f"No bot token for business {business.id}")
            return

        if token in self.bots:
            logger.info(f"Bot already registered: {business.name}")
            return

        try:
            # Create bot and dispatcher
            bot = Bot(
                token=token,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML)
            )

            dp = Dispatcher()

            # Register middleware
            dp.message.middleware(BusinessContextMiddleware(str(business.id)))
            dp.callback_query.middleware(BusinessContextMiddleware(str(business.id)))

            # Register handlers
            from aiogram import Router
            router = Router()

            register_menu_handlers(router, str(business.id))
            register_ai_handlers(router, str(business.id))

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
                f"Registered bot for {business.name} "
                f"(business_id: {business.id})"
            )

        except Exception as e:
            logger.error(f"Failed to register bot for {business.name}: {e}")

    async def get_bot(self, bot_token: str):
        """Get bot instance by token."""
        if bot_token in self.bots:
            return self.bots[bot_token]

        # Try loading from Redis cache
        cached = await self.redis.get(f"bot:{bot_token}")
        if cached:
            data = json.loads(cached)
            business = await Business.get_or_none(id=data['business_id'])
            if business:
                await self.register_bot(business)
                return self.bots.get(bot_token)

        return None

    async def get_bot_for_user(self, user_id: str):
        """
        Get bot instance for a specific user.

        This requires determining which business the user belongs to.
        You may need to adjust this based on your architecture.
        """
        # Option 1: If you store user-business relationship
        # user = await User.get_or_none(telegram_id=int(user_id)).prefetch_related('business')
        # if user and user.business:
        #     business_id = user.business.id

        # Option 2: If you use context or last interaction
        # Check Redis for last used bot
        cached_token = await self.redis.get(f"user_bot:{user_id}")
        if cached_token:
            # Redis уже возвращает строку (decode_responses=True)
            return await self.get_bot(cached_token)

        # Option 3: Default to first available bot (for single-bot setup)
        if self.bots:
            return list(self.bots.values())[0]

        return None

    async def get_bot_by_business(self, business_id: str):
        """Get bot instance by business ID."""
        token = await self.redis.get(f"business_bot:{business_id}")
        if token:
            # Redis уже возвращает строку (decode_responses=True), не нужен .decode()
            return await self.get_bot(token)

        # Fallback: search in loaded bots
        for bot_data in self.bots.values():
            if bot_data['business_id'] == business_id:
                return bot_data

        return None

    async def reload_all_bots(self):
        """Reload all bots from database."""
        await self.close_all()
        self.bots.clear()
        await self.load_active_bots()

    async def close_all(self):
        """Close all bot sessions."""
        for bot_data in self.bots.values():
            try:
                await bot_data['bot'].session.close()
            except Exception as e:
                logger.error(f"Error closing bot session: {e}")

    async def get_bots_count(self) -> int:
        """Get number of registered bots."""
        return len(self.bots)