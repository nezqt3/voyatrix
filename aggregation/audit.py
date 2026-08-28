from pathlib import Path
from urllib.parse import urlparse

import pandas as pd


BASE_DIR = Path(__file__).parent
CSV_DIR = BASE_DIR / "csv"
REPORT_FILE = BASE_DIR / "audit_report.txt"


def _read(csv_dir: Path, name: str) -> pd.DataFrame:
    return pd.read_csv(csv_dir / name, dtype=str).fillna("")


def audit(csv_dir: Path = CSV_DIR, report_file: Path = REPORT_FILE) -> dict[str, int]:
    continents = _read(csv_dir, "continents.csv")
    countries = _read(csv_dir, "countries.csv")
    cities = _read(csv_dir, "cities.csv")
    sections = _read(csv_dir, "sections.csv")
    categories = _read(csv_dir, "categories.csv")
    places = _read(csv_dir, "places.csv")

    section_ids = {
        name: set(sections.loc[sections["name"] == name, "id"])
        for name in ("Accommodation", "Restaurants/cafe")
    }

    def invalid_url(url: str) -> bool:
        if not url:
            return False
        parsed = urlparse(url)
        return (
            parsed.scheme not in {"http", "https"}
            or not parsed.netloc
            or any(ch.isspace() for ch in url)
            or "..." in url
        )

    metrics = {
        "continents": len(continents),
        "countries": len(countries),
        "cities": len(cities),
        "sections": len(sections),
        "categories": len(categories),
        "places": len(places),
        "empty_address": int((places["address"] == "").sum()),
        "empty_description": int((places["description"] == "").sum()),
        "empty_url": int((places["url"] == "").sum()),
        "empty_image_url": int((places["image_url"] == "").sum()),
        "duplicate_source_id": int(places["source_id"].duplicated().sum()),
        "duplicate_exact_place": int(
            places.duplicated(
                ["city_id", "category_id", "name", "address", "description", "url"]
            ).sum()
        ),
        "duplicate_place_name_scope": int(
            places.duplicated(["city_id", "category_id", "name"]).sum()
        ),
        "invalid_url": int(places["url"].map(invalid_url).sum()),
        "empty_accommodation_address": int(
            ((places["address"] == "") & places["section_id"].isin(section_ids["Accommodation"])).sum()
        ),
        "empty_restaurant_address": int(
            ((places["address"] == "") & places["section_id"].isin(section_ids["Restaurants/cafe"])).sum()
        ),
        "suspicious_file_urls": int(
            places["url"].str.contains(r"/File:|\.(?:jpg|jpeg|png|webp)$", case=False, regex=True).sum()
        ),
    }

    orphan_checks = {
        "orphan_country_continent_id": set(countries["continent_id"]) - set(continents["id"]),
        "orphan_city_country_id": set(cities["country_id"]) - set(countries["id"]),
        "orphan_category_section_id": set(categories["section_id"]) - set(sections["id"]),
        "orphan_place_continent_id": set(places["continent_id"]) - set(continents["id"]),
        "orphan_place_country_id": set(places["country_id"]) - set(countries["id"]),
        "orphan_place_city_id": set(places["city_id"]) - set(cities["id"]),
        "orphan_place_section_id": set(places["section_id"]) - set(sections["id"]),
        "orphan_place_category_id": set(places["category_id"]) - set(categories["id"]),
    }
    for name, values in orphan_checks.items():
        metrics[name] = len(values)

    domains = [
        urlparse(url).netloc
        for url in places["url"]
        if url
    ]
    top_domains = pd.Series(domains).value_counts().head(15)

    lines = ["Aggregation audit", ""]
    for key in sorted(metrics):
        lines.append(f"{key}: {metrics[key]}")
    lines.extend(["", "Top URL domains:"])
    lines.extend(f"{domain}: {count}" for domain, count in top_domains.items())

    suspicious = places[
        (places["url"] == "")
        | (
            (places["address"] == "")
            & places["section_id"].isin(
                section_ids["Accommodation"] | section_ids["Restaurants/cafe"]
            )
        )
        | places["url"].map(invalid_url)
        | places["url"].str.contains(r"/File:|\.(?:jpg|jpeg|png|webp)$", case=False, regex=True)
    ][["source_id", "name", "address", "url"]].head(30)
    lines.extend(["", "Suspicious sample:", suspicious.to_string(index=False)])

    report_file.parent.mkdir(parents=True, exist_ok=True)
    report_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Audit report saved to {report_file}")
    print("\n".join(lines[:20]))
    return metrics


if __name__ == "__main__":
    audit()
