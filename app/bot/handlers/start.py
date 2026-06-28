from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.bot.keyboards.catalog import countries_keyboard
from app.services.catalog_service import CatalogService


router = Router()


@router.message(CommandStart())
async def start(message: Message, catalog_service: CatalogService) -> None:
    countries = catalog_service.get_country_options()
    await message.answer(
        "Welcome! Choose a country to start exploring travel places.",
        reply_markup=countries_keyboard(countries),
    )
