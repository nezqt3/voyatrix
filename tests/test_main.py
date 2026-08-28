import asyncio
from unittest.mock import AsyncMock

from aiohttp.test_utils import make_mocked_request

from app.core.config import Settings
from app.main import create_dispatcher, create_webhook_application, health, setup_webhook


def test_health_endpoint_returns_ok():
    response = asyncio.run(health(make_mocked_request("GET", "/health")))

    assert response.status == 200
    assert response.text == '{"status": "ok"}'


def test_webhook_application_exposes_health_and_webhook_routes(csv_dir):
    settings = Settings(
        bot_token="123456:ABC",
        csv_dir=csv_dir,
        media_root=csv_dir,
        webhook_base_url="https://travel-bot.example.com",
        webhook_secret="safe_test_secret",
    )
    bot = AsyncMock()
    dispatcher = create_dispatcher(settings)

    application = create_webhook_application(bot, dispatcher, settings)
    routes = {(route.method, route.resource.canonical) for route in application.router.routes()}

    assert ("GET", "/health") in routes
    assert ("POST", "/telegram/webhook") in routes


def test_setup_webhook_configures_telegram():
    bot = AsyncMock()

    asyncio.run(
        setup_webhook(
            bot=bot,
            webhook_url="https://travel-bot.example.com/telegram/webhook",
            webhook_secret="safe_test_secret",
        )
    )

    bot.set_webhook.assert_awaited_once_with(
        url="https://travel-bot.example.com/telegram/webhook",
        secret_token="safe_test_secret",
        allowed_updates=["message", "callback_query"],
    )
