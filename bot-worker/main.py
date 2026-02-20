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
        self.pubsub_task = None  # Задача для прослушивания Redis pub/sub

    async def init_db(self):
        """Initialize database connection."""
        await Tortoise.init(
            db_url=DATABASE_URL,
            modules={"models": [
                "shared.models.business",
                "shared.models.dish",
                "shared.models.user",
                "shared.models.tg_user",
                "shared.models.table",
                "shared.models.barber",
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

    async def listen_for_reload_events(self):
        """
        Слушаем Redis pub/sub канал для команд перезагрузки ботов.
        """
        pubsub = self.redis_client.pubsub()
        await pubsub.subscribe("bot_worker:reload")

        logger.info(f"🎧 {WORKER_ID} listening for reload events...")

        try:
            async for message in pubsub.listen():
                if message['type'] == 'message':
                    logger.info(f"📨 Received reload command: {message['data']}")

                    # Перезагружаем реестр ботов
                    await self.bot_registry.reload_all_bots()

                    bots_count = await self.bot_registry.get_bots_count()
                    logger.info(f"🔄 Reloaded bot registry. Active bots: {bots_count}")

        except asyncio.CancelledError:
            logger.info(f"🛑 Pub/Sub listener stopped for {WORKER_ID}")
            await pubsub.unsubscribe("bot_worker:reload")
            await pubsub.close()
        except Exception as e:
            logger.error(f"❌ Error in pub/sub listener: {e}")

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
            logger.warning(f"⚠️ Unknown bot token: {bot_token[:10]}...")

            # Попытка перезагрузить реестр (возможно бот только что добавлен)
            logger.info("🔄 Attempting to reload bot registry...")
            await self.bot_registry.reload_all_bots()

            # Повторная попытка получить бота
            bot_data = await self.bot_registry.get_bot(bot_token)

            if not bot_data:
                logger.error(f"❌ Bot still not found after reload: {bot_token[:10]}...")
                return web.Response(status=404, text="Bot not found")

        bot = bot_data['bot']
        dp = bot_data['dispatcher']
        business_id = bot_data['business_id']

        # Получаем тело запроса для логирования
        try:
            body = await request.json()
            update_type = "unknown"
            user_id = None

            if "message" in body:
                update_type = "message"
                user_id = body["message"].get("from", {}).get("id")
            elif "callback_query" in body:
                update_type = "callback_query"
                user_id = body["callback_query"].get("from", {}).get("id")

            logger.info(
                f"📨 Webhook received: type={update_type}, "
                f"user={user_id}, business={business_id}"
            )

        except Exception as e:
            logger.error(f"Error parsing request body: {e}")

        # Обрабатываем апдейт
        try:
            # Проверяем, что у диспетчера есть зарегистрированные хендлеры
            handlers_count = len(dp.message.handlers) if hasattr(dp, 'message') else 0
            logger.info(f"🎯 Dispatcher has {handlers_count} message handlers")

            handler = SimpleRequestHandler(
                dispatcher=dp,
                bot=bot,
            )

            # Добавляем бизнес-контекст в request (для middleware)
            request['business_id'] = business_id

            logger.info(
                f"✅ Processing webhook for bot {bot_token[:10]}... "
                f"(business: {business_id})"
            )

            response = await handler.handle(request)

            logger.info(f"✅ Webhook processed successfully")
            return response

        except Exception as e:
            logger.error(
                f"❌ Error processing webhook for bot {bot_token[:10]}: {e}",
                exc_info=True
            )
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
        bots_count = await self.bot_registry.get_bots_count()
        return web.json_response({
            "status": "reloaded",
            "bots_count": bots_count
        })

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

        # Запускаем слушатель Redis pub/sub в фоне
        self.pubsub_task = asyncio.create_task(self.listen_for_reload_events())

        logger.info(f"✅ Worker {WORKER_ID} started successfully")

    async def on_shutdown(self, app: web.Application):
        """Application shutdown handler."""
        # Останавливаем слушатель pub/sub
        if self.pubsub_task:
            self.pubsub_task.cancel()
            try:
                await self.pubsub_task
            except asyncio.CancelledError:
                pass

        await self.bot_registry.close_all()
        await self.redis_client.close()
        await Tortoise.close_connections()
        logger.info(f"🛑 Worker {WORKER_ID} shutdown complete")

    def run(self, host='0.0.0.0', port=8080):
        """Run the worker."""
        self.setup_routes()
        self.app.on_startup.append(self.on_startup)
        self.app.on_shutdown.append(self.on_shutdown)

        web.run_app(self.app, host=host, port=port)


if __name__ == "__main__":
    worker = BotWorker()
    worker.run()