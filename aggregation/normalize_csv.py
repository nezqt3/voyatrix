from pathlib import Path

import pandas as pd


BASE_DIR = Path(__file__).parent
INPUT_FILE = BASE_DIR / "merged_data" / "places.csv"
OUTPUT_DIR = BASE_DIR / "csv"


def normalize(input_file: Path = INPUT_FILE, output_dir: Path = OUTPUT_DIR) -> None:
    df = pd.read_csv(input_file, dtype=str).fillna("")
    output_dir.mkdir(exist_ok=True)

    continents = df[["continent"]].drop_duplicates().reset_index(drop=True)
    continents["id"] = continents.index + 1
    continents = continents[["id", "continent"]].rename(columns={"continent": "name"})
    continents["id"] = continents["id"].astype(str)

    countries = (
        df[["continent", "country"]]
        .drop_duplicates()
        .merge(continents, left_on="continent", right_on="name")
        [["id", "country"]]
        .rename(columns={"id": "continent_id", "country": "name"})
        .drop_duplicates()
        .reset_index(drop=True)
    )
    countries["id"] = (countries.index + 1).astype(str)
    countries = countries[["id", "continent_id", "name"]]

    cities = (
        df[["country", "city"]]
        .drop_duplicates()
        .merge(countries, left_on="country", right_on="name")
        [["id", "city"]]
        .rename(columns={"id": "country_id", "city": "name"})
        .drop_duplicates()
        .reset_index(drop=True)
    )
    cities["id"] = (cities.index + 1).astype(str)
    cities = cities[["id", "country_id", "name"]]

    sections = df[["section"]].drop_duplicates().reset_index(drop=True)
    sections["id"] = (sections.index + 1).astype(str)
    sections = sections[["id", "section"]].rename(columns={"section": "name"})

    categories = (
        df[["section", "category"]]
        .drop_duplicates()
        .merge(sections, left_on="section", right_on="name")
        [["id", "category"]]
        .rename(columns={"id": "section_id", "category": "name"})
        .drop_duplicates()
        .reset_index(drop=True)
    )
    categories["id"] = (categories.index + 1).astype(str)
    categories = categories[["id", "section_id", "name"]]

    places = df.copy()
    places = (
        places.merge(continents, left_on="continent", right_on="name", how="left")
        .rename(columns={"id": "continent_id"})
        .drop(columns=["name_y"])
        .rename(columns={"name_x": "name"})
    )
    places = (
        places.merge(
            countries,
            left_on=["country", "continent_id"],
            right_on=["name", "continent_id"],
            how="left",
        )
        .rename(columns={"id": "country_id"})
        .drop(columns=["name_y"])
        .rename(columns={"name_x": "name"})
    )
    places = (
        places.merge(cities, left_on=["city", "country_id"], right_on=["name", "country_id"], how="left")
        .rename(columns={"id": "city_id"})
        .drop(columns=["name_y"])
        .rename(columns={"name_x": "name"})
    )
    places = (
        places.merge(sections, left_on="section", right_on="name", how="left")
        .rename(columns={"id": "section_id"})
        .drop(columns=["name_y"])
        .rename(columns={"name_x": "name"})
    )
    places = (
        places.merge(
            categories,
            left_on=["category", "section_id"],
            right_on=["name", "section_id"],
            how="left",
        )
        .rename(columns={"id": "category_id"})
        .drop(columns=["name_y"])
        .rename(columns={"name_x": "name"})
    )
    places["id"] = range(1, len(places) + 1)
    places["id"] = places["id"].astype(str)
    places = places[
        [
            "id",
            "source_id",
            "continent_id",
            "country_id",
            "city_id",
            "section_id",
            "category_id",
            "name",
            "address",
            "description",
            "url",
            "image_url",
        ]
    ]

    continents.to_csv(output_dir / "continents.csv", index=False)
    countries.to_csv(output_dir / "countries.csv", index=False)
    cities.to_csv(output_dir / "cities.csv", index=False)
    sections.to_csv(output_dir / "sections.csv", index=False)
    categories.to_csv(output_dir / "categories.csv", index=False)
    places.to_csv(output_dir / "places.csv", index=False)

    print(f"Normalized CSV saved to {output_dir}")


if __name__ == "__main__":
    normalize()
