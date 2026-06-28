from pathlib import Path

from app.repositories.place_repository import PlaceRepository
from app.services.catalog_service import CatalogService


def test_real_csv_catalog_flow_and_callback_sizes():
    csv_dir = Path("aggregation/csv")
    service = CatalogService(PlaceRepository(csv_dir))

    countries = service.get_country_options()
    assert countries

    country = countries[0]
    city = service.get_city_options(country["id"])[0]
    category = service.get_category_options(country["id"], city["id"])[0]
    places = service.get_places_by_ids(country["id"], city["id"], category["id"])
    place = service.get_place(places[0]["source_id"])

    assert place["country"] == country["name"]
    assert place["city"] == city["name"]
    assert place["category"] == category["name"]

    callbacks = [
        f"catalog:cities:{country['id']}::::0",
        f"catalog:categories:{country['id']}:{city['id']}:::0",
        f"catalog:places:{country['id']}:{city['id']}:{category['id']}::0",
        f"catalog:place::::{place['source_id']}:0",
    ]
    assert max(len(callback.encode()) for callback in callbacks) <= 64
