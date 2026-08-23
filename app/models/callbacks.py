from aiogram.filters.callback_data import CallbackData


class CatalogCallback(CallbackData, prefix="catalog"):
    level: str
    country_id: str | None = None
    city_id: str | None = None
    category_id: str | None = None
    place_id: str | None = None
    page: int = 0
    country_page: int = 0
    city_page: int = 0
    category_page: int = 0
