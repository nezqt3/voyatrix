import asyncio
from unittest.mock import AsyncMock

from app.bot.handlers.start import (
    BOT_COMMANDS,
    EXPLORE_BUTTON_TEXT,
    HELP_BUTTON_TEXT,
    WELCOME_TEXT,
    main_menu_keyboard,
    setup_bot_menu,
)


def test_welcome_text_explains_the_catalog_flow():
    assert "Choose a country" in WELCOME_TEXT
    assert "city and a category" in WELCOME_TEXT
    assert "/help" in WELCOME_TEXT


def test_bot_menu_contains_main_commands():
    assert [command.command for command in BOT_COMMANDS] == ["start", "help"]
    assert all(command.description for command in BOT_COMMANDS)


def test_main_menu_keyboard_is_persistent_and_has_main_actions():
    markup = main_menu_keyboard()

    assert markup.is_persistent is True
    assert markup.resize_keyboard is True
    assert [row[0].text for row in markup.keyboard] == [
        EXPLORE_BUTTON_TEXT,
        HELP_BUTTON_TEXT,
    ]


def test_setup_bot_menu_enables_telegram_commands_button():
    bot = AsyncMock()

    asyncio.run(setup_bot_menu(bot))

    bot.set_my_commands.assert_awaited_once_with(BOT_COMMANDS)
    bot.set_chat_menu_button.assert_awaited_once()
