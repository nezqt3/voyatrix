import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.bot.handlers import catalog, start
from app.core.config import Settings, get_settings
from app.core.logging import setup_logging
from app.repositories.place_repository import PlaceRepository
from app.services.catalog_service import CatalogService


def create_dispatcher(settings: Settings) -> Dispatcher:
    repository = PlaceRepository(settings.csv_dir, settings.media_root)
    catalog_service = CatalogService(repository)

    dispatcher = Dispatcher(catalog_service=catalog_service)
    dispatcher.include_router(start.router)
    dispatcher.include_router(catalog.router)
    return dispatcher


async def health(_: web.Request) -> web.Response:
    return web.json_response({"status": "ok"})


async def setup_webhook(
    bot: Bot,
    webhook_url: str,
    webhook_secret: str,
) -> None:
    await start.setup_bot_menu(bot)
    await bot.set_webhook(
        url=webhook_url,
        secret_token=webhook_secret,
        allowed_updates=["message", "callback_query"],
    )
    logging.info("Telegram webhook configured at %s", webhook_url)


async def run_polling(bot: Bot, dispatcher: Dispatcher) -> None:
    await start.setup_bot_menu(bot)
    await bot.delete_webhook(drop_pending_updates=False)
    logging.info("Travel bot started in polling mode")
    await dispatcher.start_polling(bot)


def run_webhook(
    bot: Bot,
    dispatcher: Dispatcher,
    settings: Settings,
) -> None:
    application = create_webhook_application(bot, dispatcher, settings)
    logging.info("Travel bot web service listening on %s:%s", settings.host, settings.port)
    web.run_app(application, host=settings.host, port=settings.port)


def create_webhook_application(
    bot: Bot,
    dispatcher: Dispatcher,
    settings: Settings,
) -> web.Application:
    if not settings.webhook_url:
        raise RuntimeError("A public webhook URL is required in webhook mode")
    if not settings.webhook_secret:
        raise RuntimeError("WEBHOOK_SECRET is required in webhook mode")

    dispatcher.startup.register(setup_webhook)

    application = web.Application()
    application.router.add_get("/", health)
    application.router.add_get("/health", health)
    SimpleRequestHandler(
        dispatcher=dispatcher,
        bot=bot,
        secret_token=settings.webhook_secret,
        handle_in_background=True,
    ).register(application, path=settings.webhook_path)
    setup_application(
        application,
        dispatcher,
        bot=bot,
        webhook_url=settings.webhook_url,
        webhook_secret=settings.webhook_secret,
    )
    return application


def main() -> None:
    setup_logging()
    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dispatcher = create_dispatcher(settings)

    if settings.public_base_url:
        run_webhook(bot, dispatcher, settings)
    else:
        asyncio.run(run_polling(bot, dispatcher))


if __name__ == "__main__":
    main()
