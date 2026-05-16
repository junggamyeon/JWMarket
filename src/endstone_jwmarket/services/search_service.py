

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endstone import Logger
    from endstone_jwmarket.database.repositories import AuctionRepository
    from endstone_jwmarket.cache import SearchCache


class SearchService:
    def __init__(self, auction_repo: AuctionRepository, search_cache: SearchCache, categories: dict[str, Any], logger: Logger) -> None:
        self._auction_repo = auction_repo
        self._cache = search_cache
        self._categories = categories
        self._logger = logger

    async def search(self, keyword: str, page: int = 1, per_page: int = 7) -> tuple[list, int]:
        normalized = keyword.strip().lower()
        cache_key = f"search:{normalized}:{page}:{per_page}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        offset = (page - 1) * per_page
        results = await self._auction_repo.search_listings(normalized, per_page, offset)
        count = await self._auction_repo.search_count(normalized)
        self._cache.set(cache_key, results, count)
        return results, count

    async def search_by_category(self, category: str, page: int = 1, per_page: int = 7) -> list:
        offset = (page - 1) * per_page
        return await self._auction_repo.get_listings_by_category(category, per_page, offset)

    def get_category_list(self) -> list[dict[str, str]]:
        result = []
        for key, data in self._categories.items():
            result.append({
                "key": key,
                "display_name": data.get("display_name", key.title()),
                "icon": data.get("icon", ""),
            })
        return result

    def find_category_for_item(self, item_type: str) -> str | None:
        item_lower = item_type.lower()
        for cat_key, cat_data in self._categories.items():
            items_list = cat_data.get("items", [])
            if item_lower in [i.lower() for i in items_list]:
                return cat_key
        return "misc"

    def invalidate_cache(self) -> None:
        self._cache.invalidate_all()
