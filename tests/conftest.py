from pathlib import Path

import pytest


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


@pytest.fixture
def csv_dir(tmp_path: Path) -> Path:
    _write_csv(
        tmp_path / "continents.csv",
        "id,name",
        [
            "1,Europe",
            "2,North America",
        ],
    )
    _write_csv(
        tmp_path / "countries.csv",
        "id,continent_id,name",
        [
            "10,1,France",
            "20,2,United States",
        ],
    )
    _write_csv(
        tmp_path / "cities.csv",
        "id,country_id,name",
        [
            "100,10,Paris",
            "200,20,New York",
            "201,20,Boston",
        ],
    )
    _write_csv(
        tmp_path / "sections.csv",
        "id,name",
        [
            "1000,Accommodation",
            "2000,Attractions",
        ],
    )
    _write_csv(
        tmp_path / "categories.csv",
        "id,section_id,name",
        [
            "500,1000,Hotels",
            "600,2000,Museums",
            "700,2000,Parks",
        ],
    )
    _write_csv(
        tmp_path / "places.csv",
        "id,source_id,continent_id,country_id,city_id,section_id,category_id,name,address,description,url,image_url",
        [
            "1,src-2,1,10,100,2000,600,Louvre Museum,Rue de Rivoli,Art museum,https://example.com/louvre,media/louvre.jpg",
            "2,src-1,1,10,100,1000,500,Alpha Hotel,1 Main St,Central hotel,https://example.com/hotel,media/hotel.jpg",
            "3,src-3,2,20,200,2000,700,Central Park,Manhattan,Urban park,https://example.com/park,media/park.jpg",
        ],
    )
    return tmp_path
