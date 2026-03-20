import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from bot.config import settings
from bot.database.models import Base, async_engine
from bot.middlewares.throttling import ThrottlingMiddleware
from bot.middlewares.database import DatabaseMiddleware
from bot.services.alert_service import check_alerts
from bot.services.coingecko import coingecko

from bot.handlers.start import router as start_router
from bot.handlers.portfolio import router as portfolio_router
from bot.handlers.tracking import router as tracking_router
from bot.handlers.alerts import router as alerts_router
from bot.handlers.analytics import router as analytics_router
from bot.handlers.dca import router as dca_router
from bot.handlers.settings import router as settings_router


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("cryptofolio")


async def on_startup(bot: Bot) -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        check_alerts,
        "interval",
        seconds=settings.alert_check_interval,
        args=[bot],
        id="alert_checker",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Alert scheduler started (interval: %ds)", settings.alert_check_interval)

    me = await bot.get_me()
    logger.info("Bot started: @%s", me.username)


async def on_shutdown() -> None:
    await coingecko.close()
    await async_engine.dispose()
    logger.info("Bot stopped")


async def main() -> None:
    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )

    dp = Dispatcher(storage=MemoryStorage())

    dp.message.middleware(ThrottlingMiddleware(rate_limit=0.5))
    dp.message.middleware(DatabaseMiddleware())
    dp.callback_query.middleware(DatabaseMiddleware())

    dp.include_routers(
        start_router,
        portfolio_router,
        tracking_router,
        alerts_router,
        analytics_router,
        dca_router,
        settings_router,
    )

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    logger.info("Starting CryptoFolio Bot...")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
