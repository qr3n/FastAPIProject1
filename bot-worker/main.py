# bot-worker/main.py
import asyncio
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis
from tortoise import Tortoise
import os

from bot_registry import BotRegistry
from handlers import register_handlers, register_callback_handlers
from middleware import BusinessContextMiddleware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL")
REDIS_URL = os.getenv("REDIS_URL")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
WORKER_ID = os.getenv("WORKER_ID", "worker-1")


class BotWorker:
    """Worker that handles webhooks from multiple bots."""

    def __init__(self):
        self.app = web.Application()
        self.bot_registry = None
        self.redis_client = None

    async def init_db(self):
        """Initialize database connection."""
        await Tortoise.init(
            db_url=DATABASE_URL,
            modules={"models": [
                "shared.models.business",
                "shared.models.dish",
                "shared.models.user",
                "shared.models.tg_user"
            ]}
        )
        await Tortoise.generate_schemas(safe=True)
        logger.info("Database initialized")

    async def init_redis(self):
        """Initialize Redis connection."""
        self.redis_client = redis.from_url(REDIS_URL, decode_responses=True)
        await self.redis_client.ping()
        logger.info("Redis connected")

    async def setup_bot_registry(self):
        """Setup bot registry with caching."""
        self.bot_registry = BotRegistry(self.redis_client)
        await self.bot_registry.load_active_bots()

        # Делаем реестр доступным через app context
        self.app['bot_registry'] = self.bot_registry

        logger.info(f"Bot registry initialized on {WORKER_ID}")

    async def webhook_handler(self, request: web.Request) -> web.Response:
        """
        Universal webhook handler for all bots.
        Route: /webhook/{bot_token}
        """
        bot_token = request.match_info.get('bot_token')

        if not bot_token:
            return web.Response(status=400, text="Bot token required")

        # Получаем бота и диспетчер из реестра
        bot_data = await self.bot_registry.get_bot(bot_token)

        if not bot_data:
            logger.warning(f"Unknown bot token: {bot_token[:10]}...")
            return web.Response(status=404, text="Bot not found")

        bot = bot_data['bot']
        dp = bot_data['dispatcher']
        business_id = bot_data['business_id']

        # Обрабатываем апдейт
        try:
            handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )

            # Добавляем бизнес-контекст в middleware
            request['business_id'] = business_id

            return await handler.handle(request)

        except Exception as e:
            logger.error(f"Error processing webhook for bot {bot_token[:10]}: {e}")
            return web.Response(status=500, text="Internal error")

    async def health_check(self, request: web.Request) -> web.Response:
        """Health check endpoint."""
        return web.json_response({
            "status": "healthy",
            "worker_id": WORKER_ID,
            "bots_loaded": await self.bot_registry.get_bots_count()
        })

    async def reload_bots(self, request: web.Request) -> web.Response:
        """Reload bots from database (admin endpoint)."""
        await self.bot_registry.reload_all_bots()
        return web.json_response({"status": "reloaded"})

    def setup_routes(self):
        """Setup application routes."""
        self.app.router.add_post('/webhook/{bot_token}', self.webhook_handler)
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_post('/admin/reload', self.reload_bots)

        # Регистрируем callback handlers для AI
        register_callback_handlers(self.app)

    async def on_startup(self, app: web.Application):
        """Application startup handler."""
        await self.init_db()
        await self.init_redis()
        await self.setup_bot_registry()
        logger.info(f"Worker {WORKER_ID} started successfully")

    async def on_shutdown(self, app: web.Application):
        """Application shutdown handler."""
        await self.bot_registry.close_all()
        await self.redis_client.close()
        await Tortoise.close_connections()
        logger.info(f"Worker {WORKER_ID} shutdown complete")

    def run(self, host='0.0.0.0', port=8080):
        """Run the worker."""
        self.setup_routes()
        self.app.on_startup.append(self.on_startup)
        self.app.on_shutdown.append(self.on_shutdown)

        web.run_app(self.app, host=host, port=port)


if __name__ == "__main__":
    worker = BotWorker()
    worker.run()