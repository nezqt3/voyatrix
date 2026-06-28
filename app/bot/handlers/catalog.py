from html import escape

from aiogram import Router
from aiogram.types import CallbackQuery

from app.bot.keyboards.catalog import (
    categories_keyboard,
    cities_keyboard,
    countries_keyboard,
    place_keyboard,
    places_keyboard,
)
from app.models.callbacks import CatalogCallback
from app.services.catalog_service import CatalogService


router = Router()


def _empty_text(item_name: str) -> str:
    return f"No {item_name} found. Please go back and try another option."


def _place_text(place: dict) -> str:
    description = place.get("description") or "No description available."
    if len(description) > 1800:
        description = f"{description[:1800].rstrip()}..."

    lines = [
        f"<b>{escape(place.get('name') or 'Place')}</b>",
        "",
        f"<b>Country:</b> {escape(place.get('country') or '-')}",
        f"<b>City:</b> {escape(place.get('city') or '-')}",
        f"<b>Category:</b> {escape(place.get('category') or '-')}",
    ]

    if place.get("address"):
        lines.append(f"<b>Address:</b> {escape(place['address'])}")

    lines.extend(["", escape(description)])
    return "\n".join(lines)


@router.callback_query(CatalogCallback.filter())
async def catalog_callback(
    callback: CallbackQuery,
    callback_data: CatalogCallback,
    catalog_service: CatalogService,
) -> None:
    if callback_data.level == "countries":
        countries = catalog_service.get_country_options()
        await callback.message.edit_text(
            "Choose a country:",
            reply_markup=countries_keyboard(countries, callback_data.page),
        )

    elif callback_data.level == "cities":
        cities = catalog_service.get_city_options(callback_data.country_id)
        await callback.message.edit_text(
            _empty_text("cities") if not cities else "Choose a city:",
            reply_markup=cities_keyboard(
                callback_data.country_id,
                cities,
                callback_data.page,
            ),
        )

    elif callback_data.level == "categories":
        categories = catalog_service.get_category_options(
            callback_data.country_id,
            callback_data.city_id,
        )
        await callback.message.edit_text(
            _empty_text("categories") if not categories else "Choose a category:",
            reply_markup=categories_keyboard(
                callback_data.country_id,
                callback_data.city_id,
                categories,
                callback_data.page,
            ),
        )

    elif callback_data.level == "places":
        places = catalog_service.get_places_by_ids(
            callback_data.country_id,
            callback_data.city_id,
            callback_data.category_id,
        )
        await callback.message.edit_text(
            _empty_text("places") if not places else "Choose a place:",
            reply_markup=places_keyboard(
                callback_data.country_id,
                callback_data.city_id,
                callback_data.category_id,
                places,
                callback_data.page,
            ),
        )

    elif callback_data.level == "place":
        place = catalog_service.get_place(callback_data.place_id)
        if not place:
            await callback.message.edit_text("Place not found. Please start over.")
        else:
            await callback.message.edit_text(
                _place_text(place),
                reply_markup=place_keyboard(place),
                parse_mode="HTML",
                disable_web_page_preview=False,
            )

    await callback.answer()
