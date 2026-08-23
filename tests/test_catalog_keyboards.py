from app.bot.keyboards.catalog import (
    categories_keyboard,
    cities_keyboard,
    countries_keyboard,
    place_keyboard,
    places_keyboard,
)
from app.models.callbacks import CatalogCallback


def _buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def _callback_data(button):
    return CatalogCallback.unpack(button.callback_data)


def test_country_keyboard_uses_short_country_id_callback():
    markup = countries_keyboard([{"id": "20", "name": "United States"}])
    button = _buttons(markup)[0]

    assert button.text == "United States"
    callback = _callback_data(button)
    assert callback.level == "cities"
    assert callback.country_id == "20"
    assert len(button.callback_data.encode()) <= 64


def test_keyboard_pagination_and_back_buttons():
    cities = [{"id": str(index), "name": f"City {index}"} for index in range(10)]

    first_page = cities_keyboard("20", cities)
    first_buttons = _buttons(first_page)
    assert [button.text for button in first_buttons[-4:]] == [
        "1 / 2",
        "Next ›",
        "← Back",
        "❓ Help",
    ]
    next_callback = _callback_data(first_buttons[-3])
    assert next_callback.level == "cities"
    assert next_callback.page == 1
    assert next_callback.country_id == "20"

    second_page = cities_keyboard("20", cities, page=1)
    second_buttons = _buttons(second_page)
    assert [button.text for button in second_buttons[-4:]] == [
        "‹ Previous",
        "2 / 2",
        "← Back",
        "❓ Help",
    ]
    selected_city = _callback_data(second_buttons[0])
    assert selected_city.level == "categories"
    assert selected_city.city_id == "8"
    assert selected_city.city_page == 1


def test_category_and_place_keyboards_keep_callbacks_compact():
    category_markup = categories_keyboard(
        "20",
        "200",
        [{"id": "700", "name": "Parks"}],
    )
    place_markup = places_keyboard(
        "20",
        "200",
        "700",
        [{"source_id": "paragraph_000015", "name": "Central Park"}],
    )
    place_detail_markup = place_keyboard(
        {"url": "https://example.com", "source_id": "paragraph_000015"}
    )

    category_callback = _callback_data(_buttons(category_markup)[0])
    assert category_callback.level == "places"
    assert category_callback.category_id == "700"

    place_callback = _callback_data(_buttons(place_markup)[0])
    assert place_callback.level == "place"
    assert place_callback.place_id == "paragraph_000015"
    assert place_callback.country_id == "20"
    assert place_callback.city_id == "200"
    assert place_callback.category_id == "700"
    assert _buttons(place_detail_markup)[0].url == "https://example.com"
    for markup in [category_markup, place_markup, place_detail_markup]:
        for button in _buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode()) <= 64
