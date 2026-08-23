import logging
from html import escape
from math import ceil

from aiogram import Router
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardMarkup, Message

from app.bot.keyboards.catalog import (
    PER_PAGE,
    categories_keyboard,
    cities_keyboard,
    countries_keyboard,
    help_keyboard,
    place_keyboard,
    places_keyboard,
)
from app.models.callbacks import CatalogCallback
from app.services.catalog_service import CatalogService


router = Router()

HELP_TEXT = (
    "<b>How to explore</b> 🧭\n\n"
    "1. Pick a country.\n"
    "2. Choose a city and a category.\n"
    "3. Open any place to see its photo, details, and website.\n\n"
    "Use <b>Previous</b> and <b>Next</b> to browse longer lists. "
    "The <b>Back</b> button always returns you to your previous selection.\n\n"
    "You can also send /start at any time to begin again."
)

HELP_ALERT = (
    "Choose a country, city, and category, then open a place. "
    "Use Previous, Next, and Back to move around. Send /start anytime to begin again."
)


def _empty_text(item_name: str) -> str:
    return (
        f"We couldn't find any {item_name} here yet. "
        "Go back and try another option."
    )


def _place_text(place: dict, description_limit: int = 1800) -> str:
    description = place.get("description") or "No description available yet."
    if len(description) > description_limit:
        description = f"{description[:description_limit].rstrip()}..."

    lines = [
        f"<b>{escape(place.get('name') or 'Place')}</b>",
        "",
        f"🌍 <b>Country:</b> {escape(place.get('country') or '-')}",
        f"🏙 <b>City:</b> {escape(place.get('city') or '-')}",
        f"✨ <b>Category:</b> {escape(place.get('category') or '-')}",
    ]

    if place.get("address"):
        lines.append(f"📍 <b>Address:</b> {escape(place['address'])}")

    lines.extend(["", escape(description)])
    return "\n".join(lines)


def _page_text(title: str, item_count: int, page: int, hint: str) -> str:
    total_pages = max(1, ceil(item_count / PER_PAGE))
    safe_page = min(max(page, 0), total_pages - 1)
    return (
        f"<b>{title}</b>\n"
        f"{hint}\n\n"
        f"Page {safe_page + 1} of {total_pages} · {item_count} options"
    )


async def _delete_quietly(message: Message) -> None:
    try:
        await message.delete()
    except TelegramAPIError:
        logging.debug("Could not delete the previous catalog message", exc_info=True)


async def _show_text(
    message: Message,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    if message.photo or message.video or message.document:
        await message.answer(text, reply_markup=reply_markup, parse_mode="HTML")
        await _delete_quietly(message)
        return

    try:
        await message.edit_text(text, reply_markup=reply_markup, parse_mode="HTML")
    except TelegramAPIError as error:
        if "message is not modified" not in str(error).lower():
            raise


def _photo_source(place: dict) -> str | FSInputFile | None:
    image_url = place.get("image_url") or ""
    if image_url.startswith(("http://", "https://")):
        return image_url
    if place.get("image_path"):
        return FSInputFile(place["image_path"])
    return None


async def _show_place(
    message: Message,
    place: dict,
    reply_markup: InlineKeyboardMarkup,
) -> None:
    photo = _photo_source(place)
    if not photo:
        await _show_text(message, _place_text(place), reply_markup)
        return

    try:
        await message.answer_photo(
            photo=photo,
            caption=_place_text(place, description_limit=650),
            reply_markup=reply_markup,
            parse_mode="HTML",
        )
    except TelegramAPIError:
        logging.warning(
            "Could not send image for place %s; showing text card instead",
            place.get("source_id"),
            exc_info=True,
        )
        await _show_text(message, _place_text(place), reply_markup)
        return

    await _delete_quietly(message)


@router.callback_query(CatalogCallback.filter())
async def catalog_callback(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    catalog_service: CatalogService,
) -> None:
    if callback_data.level == "noop":
        await callback.answer("You're already on this page.")
        return

    if callback_data.level == "help":
        await callback.answer(HELP_ALERT, show_alert=True)
        return

    await callback.answer()
    message = callback.message
    if not isinstance(message, Message):
        return

    if callback_data.level == "countries":
        countries = catalog_service.get_country_options()
        text = _page_text(
            "Where would you like to go? 🌍",
            len(countries),
            callback_data.page,
            "Choose a country and let's find something memorable.",
        )
        await _show_text(
            message,
            text,
            countries_keyboard(countries, callback_data.page),
        )

    elif callback_data.level == "cities":
        cities = catalog_service.get_city_options(callback_data.country_id)
        text = _empty_text("cities") if not cities else _page_text(
            "Choose your city 🏙",
            len(cities),
            callback_data.page,
            "Pick the city you'd like to explore.",
        )
        await _show_text(
            message,
            text,
            cities_keyboard(
                callback_data.country_id,
                cities,
                callback_data.page,
                callback_data.country_page,
            ),
        )

    elif callback_data.level == "categories":
        categories = catalog_service.get_category_options(
            callback_data.country_id,
            callback_data.city_id,
        )
        text = _empty_text("categories") if not categories else _page_text(
            "What are you in the mood for? ✨",
            len(categories),
            callback_data.page,
            "Choose a category to narrow down the best matches.",
        )
        await _show_text(
            message,
            text,
            categories_keyboard(
                callback_data.country_id,
                callback_data.city_id,
                categories,
                callback_data.page,
                callback_data.country_page,
                callback_data.city_page,
            ),
        )

    elif callback_data.level == "places":
        places = catalog_service.get_places_by_ids(
            callback_data.country_id,
            callback_data.city_id,
            callback_data.category_id,
        )
        text = _empty_text("places") if not places else _page_text(
            "Places worth exploring 📍",
            len(places),
            callback_data.page,
            "Tap a place for its photo, details, and website.",
        )
        await _show_text(
            message,
            text,
            places_keyboard(
                callback_data.country_id,
                callback_data.city_id,
                callback_data.category_id,
                places,
                callback_data.page,
                callback_data.country_page,
                callback_data.city_page,
                callback_data.category_page,
            ),
        )

    elif callback_data.level == "place":
        place = catalog_service.get_place(callback_data.place_id)
        if not place:
            await _show_text(
                message,
                "This place is no longer available. Please start over.",
                countries_keyboard(catalog_service.get_country_options()),
            )
        else:
            markup = place_keyboard(
                place,
                country_id=callback_data.country_id or "",
                city_id=callback_data.city_id or "",
                category_id=callback_data.category_id or "",
                page=callback_data.page,
                country_page=callback_data.country_page,
                city_page=callback_data.city_page,
                category_page=callback_data.category_page,
            )
            await _show_place(message, place, markup)
