from app.repositories.place_repository import PlaceRepository
from app.services.catalog_service import CatalogService


def test_service_exposes_catalog_flow(csv_dir):
    service = CatalogService(PlaceRepository(csv_dir))

    country = service.get_country_options()[0]
    city = service.get_city_options(country["id"])[0]
    category = service.get_category_options(country["id"], city["id"])[0]
    places = service.get_places_by_ids(country["id"], city["id"], category["id"])

    assert country == {"id": "10", "name": "France"}
    assert city == {"id": "100", "name": "Paris"}
    assert category == {"id": "500", "name": "Hotels"}
    assert places[0]["name"] == "Alpha Hotel"
    assert service.get_place(places[0]["source_id"])["city"] == "Paris"
