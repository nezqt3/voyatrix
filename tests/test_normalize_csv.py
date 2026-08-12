import pandas as pd

from aggregation.normalize_csv import normalize


def test_normalize_creates_related_csv_files(tmp_path):
    merged_dir = tmp_path / "merged_data"
    merged_dir.mkdir()
    input_file = merged_dir / "places.csv"
    output_dir = tmp_path / "csv"

    pd.DataFrame(
        [
            {
                "source_id": "p1",
                "continent": "Europe",
                "country": "France",
                "city": "Paris",
                "section": "Attractions",
                "category": "Museums",
                "name": "Louvre",
                "address": "Rue de Rivoli",
                "description": "Museum",
                "url": "https://example.com/louvre?keep=1",
                "image_url": "media/louvre.jpg",
            }
        ]
    ).to_csv(input_file, index=False)

    normalize(input_file=input_file, output_dir=output_dir)

    places = pd.read_csv(output_dir / "places.csv", dtype=str).fillna("")
    countries = pd.read_csv(output_dir / "countries.csv", dtype=str).fillna("")
    cities = pd.read_csv(output_dir / "cities.csv", dtype=str).fillna("")
    categories = pd.read_csv(output_dir / "categories.csv", dtype=str).fillna("")

    assert places.loc[0, "url"] == "https://example.com/louvre?keep=1"
    assert countries.loc[0, "name"] == "France"
    assert cities.loc[0, "country_id"] == countries.loc[0, "id"]
    assert categories.loc[0, "name"] == "Museums"
    assert places.loc[0, "category_id"] == categories.loc[0, "id"]
