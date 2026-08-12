from aggregation.helper import (
    is_implicit_city_heading,
    is_implicit_object_start,
    is_numbered_geo_heading,
    is_probable_address,
    normalize_url,
    split_inline_uk_address,
    split_object_text,
)
from aggregation.merge_places import image_url


def test_normalize_url_preserves_query_parameters():
    url = "https://example.com/path?activity=123&lang=en#details"

    assert normalize_url(url) == url


def test_normalize_url_repairs_known_broken_source_links():
    assert normalize_url(
        "https://en.wikipedia.org/wiki/Tower_Bridge#/media/File:Tower_Bridge_at_Dawn.jpg"
    ) == "https://en.wikipedia.org/wiki/Tower_Bridge"


def test_image_url_preserves_external_images():
    assert image_url("image1.jpg") == "media/image1.jpg"
    assert image_url("https://example.com/image.jpg?size=large") == (
        "https://example.com/image.jpg?size=large"
    )


def test_probable_address_does_not_treat_descriptions_as_addresses():
    assert is_probable_address("215 West 94th Street, New York, NY 10025")
    assert is_probable_address("Calle de las Huertas 24, 28014 Madrid Spain")
    assert is_probable_address("Đường xuyên đảo Cát Bà, Cat Ba, Vietnam")
    assert not is_probable_address(
        "A lighter version of rafting in a smaller boat, designed for families."
    )
    assert not is_probable_address(
        "Times Square is a commercial intersection, tourist destination, and entertainment hub."
    )
    assert not is_probable_address(
        "Opened in 2000, the wheel rises 135 metres, and contains 32 capsules."
    )
    assert not is_probable_address("Various operators via Pelago")
    assert not is_probable_address("Ancient Culture Street Tour (up to 3 guests)")
    assert not is_probable_address("Single climbing attempt: R$ 25, package prices vary")


def test_probable_address_allows_punctuation_for_address_heavy_sections():
    assert is_probable_address(
        "30 Henrietta Street, Covent Garden, London, WC2E 8NA.",
        allow_terminal_punctuation=True,
    )
    assert not is_probable_address(
        "Located in San Diego and 1.2 mi from downtown, the hotel offers free Wi-Fi.",
        allow_terminal_punctuation=True,
    )
    assert not is_probable_address("https://example.com/place")


def test_split_object_text_keeps_inline_description_out_of_name():
    name, description = split_object_text(
        "2) Madrid City Tour (48-Hour Ticket)Same as above, but longer."
    )

    assert name == "Madrid City Tour (48-Hour Ticket)"
    assert description == "Same as above, but longer."


def test_split_object_text_accepts_number_without_space():
    name, description = split_object_text("1)House of Gods Royal Mile")

    assert name == "House of Gods Royal Mile"
    assert description == ""


def test_split_object_text_cleans_inconsistent_numbering():
    assert split_object_text("6.)The National Gallery")[0] == "The National Gallery"
    assert split_object_text("2) 2.British Museum")[0] == "British Museum"
    assert split_object_text("3).Up at The O2")[0] == "Up at The O2"


def test_inline_uk_address_is_removed_from_name():
    name, address = split_inline_uk_address(
        "Tower Bridge (Tower Bridge Rd, London SE1 2UP, UK.) 21$"
    )
    assert name == "Tower Bridge (21$)"
    assert address == "Tower Bridge Rd, London SE1 2UP, UK"


def test_numbered_geo_heading_does_not_consume_uppercase_place_name():
    rows = [
        {"type": "text", "text": "1) EUROPE"},
        {"type": "text", "text": "7) THE UNITED ARAB EMIRATES (UAE)"},
        {"type": "text", "text": "- Dubai"},
        {"type": "text", "text": "1) URBAN HOTEL"},
        {"type": "text", "text": "4025 Debrecen, 17 Hatvan utca, Hungary"},
    ]
    continents = {"EUROPE"}

    assert is_numbered_geo_heading(rows, 0, continents)
    assert is_numbered_geo_heading(rows, 1, continents)
    assert not is_numbered_geo_heading(rows, 3, continents)


def test_implicit_city_heading_before_accommodation():
    rows = [
        {"type": "text", "text": "Hong Kong"},
        {"type": "text", "text": "Accommodation (жилье)"},
    ]

    assert is_implicit_city_heading(rows, 0, "Transport")
    assert not is_implicit_city_heading(rows, 0, "Attractions")


def test_implicit_object_requires_url_before_next_numbered_object():
    place_rows = [
        {"type": "text", "text": "Cora Pearl ($23-113)"},
        {"type": "text", "text": "30 Henrietta Street, London"},
        {"type": "text", "text": "https://example.com/cora-pearl"},
    ]
    category_rows = [
        {"type": "text", "text": "Hotels"},
        {"type": "image", "image": "hotel.jpg"},
        {"type": "text", "text": "1) Hotel One"},
        {"type": "text", "text": "https://example.com/hotel"},
    ]

    assert is_implicit_object_start(place_rows, 0)
    assert not is_implicit_object_start(category_rows, 0)
