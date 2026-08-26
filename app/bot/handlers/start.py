from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    BotCommand,
    KeyboardButton,
    MenuButtonCommands,
    Message,
    ReplyKeyboardMarkup,
)

from app.bot.handlers.catalog import HELP_TEXT
from app.bot.keyboards.catalog import countries_keyboard, help_keyboard
from app.services.catalog_service import CatalogService


router = Router()

EXPLORE_BUTTON_TEXT = "🌍 Choose a country"
HELP_BUTTON_TEXT = "❓ How to use the bot"

WELCOME_TEXT = (
    "<b>Hi! I'll help you find interesting places for your trip</b> ✈️\n\n"
    "It's easy to get started:\n"
    "1. Choose a country.\n"
    "2. Select a city and a category.\n"
    "3. Open a place to see its photo, description, and website.\n\n"
    "Choose a country below. If you need help, send /help or tap "
    "<b>❓ How to use the bot</b> in the menu."
)

BOT_COMMANDS = [
    BotCommand(command="start", description="Start exploring"),
    BotCommand(command="help", description="How to use the bot"),
]


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Build the persistent menu displayed next to Telegram's input field."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=EXPLORE_BUTTON_TEXT)],
            [KeyboardButton(text=HELP_BUTTON_TEXT)],
        ],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder="Choose an option",
    )


async def setup_bot_menu(bot: Bot) -> None:
    """Show the bot commands in Telegram's persistent menu button."""
    await bot.set_my_commands(BOT_COMMANDS)
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())


async def _send_welcome(
    message: Message,
    catalog_service: CatalogService,
) -> None:
    countries = catalog_service.get_country_options()
    await message.answer(
        WELCOME_TEXT,
        reply_markup=main_menu_keyboard(),
        parse_mode="HTML",
    )
    await message.answer(
        "<b>Where would you like to go?</b> Choose a country:",
        reply_markup=countries_keyboard(countries),
        parse_mode="HTML",
    )


@router.message(CommandStart())
async def start(message: Message, catalog_service: CatalogService) -> None:
    await _send_welcome(message, catalog_service)


@router.message(F.text == EXPLORE_BUTTON_TEXT)
async def explore_from_menu(
    message: Message,
    catalog_service: CatalogService,
) -> None:
    countries = catalog_service.get_country_options()
    await message.answer(
        "<b>Choose a country</b> 🌍",
        reply_markup=countries_keyboard(countries),
        parse_mode="HTML",
    )


@router.message(F.text == HELP_BUTTON_TEXT)
async def help_from_menu(message: Message) -> None:
    await help_command(message)


@router.message(Command("help"))
async def help_command(message: Message) -> None:
    await message.answer(HELP_TEXT, reply_markup=help_keyboard(), parse_mode="HTML")
