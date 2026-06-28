from app.bot.keyboards.catalog import (
    categories_keyboard,
    cities_keyboard,
    countries_keyboard,
    place_keyboard,
    places_keyboard,
)


def _buttons(markup):
    return [button for row in markup.inline_keyboard for button in row]


def test_country_keyboard_uses_short_country_id_callback():
    markup = countries_keyboard([{"id": "20", "name": "United States"}])
    button = _buttons(markup)[0]

    assert button.text == "United States"
    assert button.callback_data == "catalog:cities:20::::0"
    assert len(button.callback_data.encode()) <= 64


def test_keyboard_pagination_and_back_buttons():
    cities = [{"id": str(index), "name": f"City {index}"} for index in range(10)]

    first_page = cities_keyboard("20", cities)
    first_buttons = _buttons(first_page)
    assert [button.text for button in first_buttons[-2:]] == ["Next", "Back"]
    assert first_buttons[-2].callback_data == "catalog:categories:20::::1"

    second_page = cities_keyboard("20", cities, page=1)
    second_buttons = _buttons(second_page)
    assert [button.text for button in second_buttons[-2:]] == ["Previous", "Back"]
    assert second_buttons[0].callback_data == "catalog:categories:20:8:::0"


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

    assert _buttons(category_markup)[0].callback_data == "catalog:places:20:200:700::0"
    assert _buttons(place_markup)[0].callback_data == "catalog:place::::paragraph_000015:0"
    assert _buttons(place_detail_markup)[0].url == "https://example.com"
    for markup in [category_markup, place_markup, place_detail_markup]:
        for button in _buttons(markup):
            if button.callback_data:
                assert len(button.callback_data.encode()) <= 64
