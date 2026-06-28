import asyncio
import logging

from aiogram import Bot, Dispatcher

from app.bot.handlers import catalog, start
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.repositories.place_repository import PlaceRepository
from app.services.catalog_service import CatalogService


async def main() -> None:
    setup_logging()
    settings = get_settings()

    repository = PlaceRepository(settings.csv_dir)
    catalog_service = CatalogService(repository)

    bot = Bot(token=settings.bot_token)
    dispatcher = Dispatcher(catalog_service=catalog_service)
    dispatcher.include_router(start.router)
    dispatcher.include_router(catalog.router)

    logging.info("Travel bot started")
    await dispatcher.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
