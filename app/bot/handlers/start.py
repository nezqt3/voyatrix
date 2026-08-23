from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.bot.handlers.catalog import HELP_TEXT
from app.bot.keyboards.catalog import countries_keyboard, help_keyboard
from app.services.catalog_service import CatalogService


router = Router()


@router.message(CommandStart())
async def start(message: Message, catalog_service: CatalogService) -> None:
    countries = catalog_service.get_country_options()
    await message.answer(
        "<b>Ready for your next adventure?</b> ✈️\n\n"
        "Explore hand-picked places around the world — from iconic sights "
        "to great stays, food, and local experiences.\n\n"
        "Choose a country to get started:",
        reply_markup=countries_keyboard(countries),
        parse_mode="HTML",
    )


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_keyboard(), parse_mode="HTML")
