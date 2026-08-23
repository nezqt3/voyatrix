from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.models.callbacks import CatalogCallback


PER_PAGE = 8


def _callback(level: str, page: int = 0, **context) -> str:
    return CatalogCallback(level=level, page=page, **context).pack()


def _safe_page(page: int, item_count: int) -> int:
    last_page = max(0, ceil(item_count / PER_PAGE) - 1)
    return min(max(page, 0), last_page)


def _navigation_row(
    builder: InlineKeyboardBuilder,
    *,
    level: str,
    page: int,
    item_count: int,
    context: dict,
) -> None:
    total_pages = max(1, ceil(item_count / PER_PAGE))
    buttons: list[InlineKeyboardButton] = []

    if page > 0:
        buttons.append(
            InlineKeyboardButton(
                text="‹ Previous",
                callback_data=_callback(level, page=page - 1, **context),
            )
        )

    buttons.append(
        InlineKeyboardButton(
            text=f"{page + 1} / {total_pages}",
            callback_data=_callback("noop"),
        )
    )

    if page + 1 < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="Next ›",
                callback_data=_callback(level, page=page + 1, **context),
            )
        )

    builder.row(*buttons)


def _options_keyboard(
    options: list[dict[str, str]],
    list_level: str,
    button_level: str,
    id_field: str,
    page: int = 0,
    back_callback: str | None = None,
    selected_context: dict | None = None,
    **context,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page = _safe_page(page, len(options))
    start = page * PER_PAGE
    end = start + PER_PAGE

    for option in options[start:end]:
        callback_context = {
            **context,
            **(selected_context or {}),
            id_field: option["id"],
        }
        builder.row(
            InlineKeyboardButton(
                text=option["name"],
                callback_data=_callback(button_level, page=0, **callback_context),
            )
        )

    _navigation_row(
        builder,
        level=list_level,
        page=page,
        item_count=len(options),
        context=context,
    )

    if back_callback:
        builder.row(InlineKeyboardButton(text="← Back", callback_data=back_callback))

    builder.row(
        InlineKeyboardButton(text="❓ Help", callback_data=_callback("help"))
    )
    return builder.as_markup()


def countries_keyboard(
    countries: list[dict[str, str]],
    page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(
        countries,
        "countries",
        "cities",
        "country_id",
        page=page,
        selected_context={"country_page": _safe_page(page, len(countries))},
    )


def cities_keyboard(
    country_id: str,
    cities: list[dict[str, str]],
    page: int = 0,
    country_page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(
        cities,
        "cities",
        "categories",
        "city_id",
        page=page,
        country_id=country_id,
        country_page=country_page,
        selected_context={"city_page": _safe_page(page, len(cities))},
        back_callback=_callback("countries", page=country_page),
    )


def categories_keyboard(
    country_id: str,
    city_id: str,
    categories: list[dict[str, str]],
    page: int = 0,
    country_page: int = 0,
    city_page: int = 0,
) -> InlineKeyboardMarkup:
    return _options_keyboard(
        categories,
        "categories",
        "places",
        "category_id",
        page=page,
        country_id=country_id,
        city_id=city_id,
        country_page=country_page,
        city_page=city_page,
        selected_context={"category_page": _safe_page(page, len(categories))},
        back_callback=_callback(
            "cities",
            page=city_page,
            country_id=country_id,
            country_page=country_page,
        ),
    )


def places_keyboard(
    country_id: str,
    city_id: str,
    category_id: str,
    places: list[dict],
    page: int = 0,
    country_page: int = 0,
    city_page: int = 0,
    category_page: int = 0,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    page = _safe_page(page, len(places))
    start = page * PER_PAGE
    end = start + PER_PAGE

    for place in places[start:end]:
        builder.row(
            InlineKeyboardButton(
                text=(place.get("name") or "Place")[:64],
                callback_data=_callback(
                    "place",
                    page=page,
                    country_id=country_id,
                    city_id=city_id,
                    category_id=category_id,
                    place_id=place["source_id"],
                    country_page=country_page,
                    city_page=city_page,
                    category_page=category_page,
                ),
            )
        )

    navigation_context = {
        "country_id": country_id,
        "city_id": city_id,
        "category_id": category_id,
        "country_page": country_page,
        "city_page": city_page,
        "category_page": category_page,
    }
    _navigation_row(
        builder,
        level="places",
        page=page,
        item_count=len(places),
        context=navigation_context,
    )

    builder.row(
        InlineKeyboardButton(
            text="← Back",
            callback_data=_callback(
                "categories",
                page=category_page,
                country_id=country_id,
                city_id=city_id,
                country_page=country_page,
                city_page=city_page,
            ),
        )
    )
    builder.row(
        InlineKeyboardButton(text="❓ Help", callback_data=_callback("help"))
    )
    return builder.as_markup()


def place_keyboard(
    place: dict,
    *,
    country_id: str = "",
    city_id: str = "",
    category_id: str = "",
    page: int = 0,
    country_page: int = 0,
    city_page: int = 0,
    category_page: int = 0,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    if place.get("url"):
        builder.row(InlineKeyboardButton(text="🔗 Open website", url=place["url"]))

    if country_id and city_id and category_id:
        builder.row(
            InlineKeyboardButton(
                text="← Back to places",
                callback_data=_callback(
                    "places",
                    page=page,
                    country_id=country_id,
                    city_id=city_id,
                    category_id=category_id,
                    country_page=country_page,
                    city_page=city_page,
                    category_page=category_page,
                ),
            )
        )

    builder.row(
        InlineKeyboardButton(
            text="🌍 Explore another country",
            callback_data=_callback("countries"),
        )
    )
    return builder.as_markup()


def help_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🌍 Start exploring",
            callback_data=_callback("countries"),
        )
    )
    return builder.as_markup()
