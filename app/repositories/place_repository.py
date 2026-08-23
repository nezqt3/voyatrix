from pathlib import Path

import pandas as pd


class PlaceRepository:
    def __init__(
        self,
        csv_dir: str | Path,
        media_root: str | Path | None = None,
    ):
        self.csv_dir = Path(csv_dir)
        self.media_root = (
            Path(media_root) if media_root else self.csv_dir.parent / "export"
        )
        self.continents = self._read_csv("continents.csv")
        self.countries = self._read_csv("countries.csv")
        self.cities = self._read_csv("cities.csv")
        self.sections = self._read_csv("sections.csv")
        self.categories = self._read_csv("categories.csv")
        self.places = self._read_csv("places.csv")

        self._country_names = self._names_by_id(self.countries)
        self._city_names = self._names_by_id(self.cities)
        self._category_names = self._names_by_id(self.categories)
        self._section_names = self._names_by_id(self.sections)
        self._continent_names = self._names_by_id(self.continents)

    def _read_csv(self, filename: str) -> pd.DataFrame:
        return pd.read_csv(self.csv_dir / filename, dtype=str).fillna("")

    @staticmethod
    def _names_by_id(df: pd.DataFrame) -> dict[str, str]:
        return dict(zip(df["id"], df["name"], strict=False))

    @staticmethod
    def _options(df: pd.DataFrame) -> list[dict[str, str]]:
        rows = df[["id", "name"]].drop_duplicates().sort_values("name")
        return rows.to_dict("records")

    def get_countries(self, continent_id: str | None = None) -> list[str]:
        df = self.countries
        if continent_id:
            df = df[df["continent_id"] == continent_id]
        return [option["name"] for option in self._options(df)]

    def get_cities(self, country_id: str) -> list[str]:
        df = self.cities[self.cities["country_id"] == country_id]
        return [option["name"] for option in self._options(df)]

    def get_categories(self, city_id: str) -> list[str]:
        category_ids = self.places[self.places["city_id"] == city_id]["category_id"].unique()
        df = self.categories[self.categories["id"].isin(category_ids)]
        return [option["name"] for option in self._options(df)]

    def get_places(self, city_id: str, category_id: str) -> list[dict]:
        df = self.places[
            (self.places["city_id"] == city_id)
            & (self.places["category_id"] == category_id)
        ].sort_values("name")
        return [self._enrich_place(row) for row in df.to_dict("records")]

    def get_place_by_id(self, source_id: str) -> dict | None:
        df = self.places[self.places["source_id"] == source_id]
        if df.empty:
            return None
        return self._enrich_place(df.iloc[0].to_dict())

    def get_country_options(self) -> list[dict[str, str]]:
        return self._options(self.countries)

    def get_city_options(self, country_id: str) -> list[dict[str, str]]:
        df = self.cities[self.cities["country_id"] == country_id]
        return self._options(df)

    def get_category_options(
        self,
        country_id: str,
        city_id: str,
    ) -> list[dict[str, str]]:
        df = self.places[
            (self.places["country_id"] == country_id)
            & (self.places["city_id"] == city_id)
        ]
        category_ids = df["category_id"].unique()
        return self._options(self.categories[self.categories["id"].isin(category_ids)])

    def get_places_by_ids(
        self,
        country_id: str,
        city_id: str,
        category_id: str,
    ) -> list[dict]:
        df = self.places[
            (self.places["country_id"] == country_id)
            & (self.places["city_id"] == city_id)
            & (self.places["category_id"] == category_id)
        ].sort_values("name")
        return [self._enrich_place(row) for row in df.to_dict("records")]

    def _enrich_place(self, place: dict) -> dict:
        country_id = place.get("country_id", "")
        city_id = place.get("city_id", "")
        category_id = place.get("category_id", "")
        section_id = place.get("section_id", "")
        continent_id = place.get("continent_id", "")

        image_url = place.get("image_url", "")
        image_path = self._resolve_image_path(image_url)

        return {
            **place,
            "continent": self._continent_names.get(continent_id, ""),
            "country": self._country_names.get(country_id, ""),
            "city": self._city_names.get(city_id, ""),
            "section": self._section_names.get(section_id, ""),
            "category": self._category_names.get(category_id, ""),
            "image_path": str(image_path) if image_path else "",
        }

    def _resolve_image_path(self, image_url: str) -> Path | None:
        if not image_url or image_url.startswith(("http://", "https://")):
            return None

        relative_path = Path(image_url)
        candidates = (
            self.media_root / relative_path,
            self.csv_dir / relative_path,
            self.csv_dir.parent / relative_path,
        )
        return next((path.resolve() for path in candidates if path.is_file()), None)
