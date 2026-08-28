from app.repositories.place_repository import PlaceRepository


def test_country_city_and_category_options_are_filtered(csv_dir):
    repository = PlaceRepository(csv_dir)

    assert repository.get_country_options() == [
        {"id": "10", "name": "France"},
        {"id": "20", "name": "United States"},
    ]
    assert repository.get_city_options("20") == [
        {"id": "201", "name": "Boston"},
        {"id": "200", "name": "New York"},
    ]
    assert repository.get_category_options("10", "100") == [
        {"id": "500", "name": "Hotels"},
        {"id": "600", "name": "Museums"},
    ]


def test_places_are_filtered_sorted_and_enriched(csv_dir):
    repository = PlaceRepository(csv_dir)

    places = repository.get_places_by_ids("10", "100", "500")

    assert [place["name"] for place in places] == ["Alpha Hotel"]
    assert places[0]["continent"] == "Europe"
    assert places[0]["country"] == "France"
    assert places[0]["city"] == "Paris"
    assert places[0]["section"] == "Accommodation"
    assert places[0]["category"] == "Hotels"


def test_place_lookup_returns_enriched_place_or_none(csv_dir):
    repository = PlaceRepository(csv_dir)

    place = repository.get_place_by_id("src-2")

    assert place["name"] == "Louvre Museum"
    assert place["country"] == "France"
    assert place["category"] == "Museums"
    assert repository.get_place_by_id("missing") is None


def test_place_lookup_resolves_local_image_from_media_root(csv_dir, tmp_path):
    media_root = tmp_path / "export"
    image = media_root / "media" / "louvre.jpg"
    image.parent.mkdir(parents=True)
    image.write_bytes(b"image")
    repository = PlaceRepository(csv_dir, media_root=media_root)

    place = repository.get_place_by_id("src-2")

    assert place["image_path"] == str(image.resolve())


def test_legacy_name_methods_still_use_normalized_ids(csv_dir):
    repository = PlaceRepository(csv_dir)

    assert repository.get_countries("1") == ["France"]
    assert repository.get_cities("20") == ["Boston", "New York"]
    assert repository.get_categories("100") == ["Hotels", "Museums"]
    assert [place["source_id"] for place in repository.get_places("100", "600")] == [
        "src-2"
    ]


def test_repository_reloads_catalog_after_atomic_places_replacement(csv_dir, tmp_path):
    repository = PlaceRepository(csv_dir)
    places_file = csv_dir / "places.csv"
    replacement = tmp_path / "places.csv"
    replacement.write_text(
        places_file.read_text(encoding="utf-8").replace("Louvre Museum", "New Louvre"),
        encoding="utf-8",
    )
    replacement.replace(places_file)

    place = repository.get_place_by_id("src-2")

    assert place is not None
    assert place["name"] == "New Louvre"
