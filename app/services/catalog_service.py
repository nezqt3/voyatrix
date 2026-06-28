class CatalogService:
    def __init__(self, repository):
        self.repository = repository

    def get_countries(self):
        return self.repository.get_countries()

    def get_cities(self, country_id: str):
        return self.repository.get_cities(country_id)

    def get_categories(self, city_id: str):
        return self.repository.get_categories(city_id)

    def get_places(self, city_id: str, category_id: str):
        return self.repository.get_places(city_id, category_id)

    def get_place(self, place_id: str):
        return self.repository.get_place_by_id(place_id)

    def get_country_options(self):
        return self.repository.get_country_options()

    def get_city_options(self, country_id: str):
        return self.repository.get_city_options(country_id)

    def get_category_options(self, country_id: str, city_id: str):
        return self.repository.get_category_options(country_id, city_id)

    def get_places_by_ids(self, country_id: str, city_id: str, category_id: str):
        return self.repository.get_places_by_ids(country_id, city_id, category_id)
