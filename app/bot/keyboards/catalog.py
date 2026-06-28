from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models.callbacks import CatalogCallback


PER_PAGE = 8


def _callback(level: str, page: int = 0, **context) -> str:
    return CatalogCallback(level=level, page=page, **context).pack()


def _options_keyboard(
    options: list[dict[str, str]],
    button_level: str,
    id_field: str,
    page: int = 0,
    back_callback: str | None = None,
    **context,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PER_PAGE
    end = start + PER_PAGE

    for option in options[start:end]:
        builder.button(
            text=option["name"],
            callback_data=_callback(
                button_level,
                page=0,
                **context,
                **{id_field: option["id"]},
            ),
        )

    if page > 0:
        builder.button(
            text="Previous",
            callback_data=_callback(button_level, page=page - 1, **context),
        )

    if end < len(options):
        builder.button(
            text="Next",
            callback_data=_callback(button_level, page=page + 1, **context),
        )

    if back_callback:
        builder.button(text="Back", callback_data=back_callback)

    builder.adjust(1)
    return builder.as_markup()


def countries_keyboard(
    countries: list[dict[str, str]],
    page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(countries, "cities", "country_id", page=page)


def cities_keyboard(
    country_id: str,
    cities: list[dict[str, str]],
    page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(
        cities,
        "categories",
        "city_id",
        page=page,
        country_id=country_id,
        back_callback=_callback("countries"),
    )


def categories_keyboard(
    country_id: str,
    city_id: str,
    categories: list[dict[str, str]],
    page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(
        categories,
        "places",
        "category_id",
        page=page,
        country_id=country_id,
        city_id=city_id,
        back_callback=_callback("cities", country_id=country_id),
    )


def places_keyboard(
    country_id: str,
    city_id: str,
    category_id: str,
    places: list[dict],
    page: int = 0,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * PER_PAGE
    end = start + PER_PAGE

    for place in places[start:end]:
        builder.button(
            text=(place.get("name") or "Place")[:64],
            callback_data=_callback("place", place_id=place["source_id"]),
        )

    if page > 0:
        builder.button(
            text="Previous",
            callback_data=_callback(
                "places",
                page=page - 1,
                country_id=country_id,
                city_id=city_id,
                category_id=category_id,
            ),
        )

    if end < len(places):
        builder.button(
            text="Next",
            callback_data=_callback(
                "places",
                page=page + 1,
                country_id=country_id,
                city_id=city_id,
                category_id=category_id,
            ),
        )

    builder.button(
        text="Back",
        callback_data=_callback(
            "categories",
            country_id=country_id,
            city_id=city_id,
        ),
    )
    builder.adjust(1)
    return builder.as_markup()


def place_keyboard(place: dict) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if place.get("url"):
        builder.button(text="Open link", url=place["url"])

    builder.button(text="Start over", callback_data=_callback("countries"))
    builder.adjust(1)
    return builder.as_markup()
