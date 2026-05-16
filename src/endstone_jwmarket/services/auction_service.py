

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endstone import Logger
    from jweconomy.api.economy_api import EconomyAPI
    from jwmarket.database.repositories.auction_repository import AuctionRepository, AuctionRecord
    from jwmarket.database.repositories.claims_repository import ClaimsRepository
    from jwmarket.cache.listing_cache import ListingCache
    from jwmarket.util.item_serializer import ItemSerializer


@dataclass(frozen=True, slots=True)
class ListingResult:
    success: bool
    listing_id: int = 0
    tax_amount: float = 0.0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class PurchaseResult:
    success: bool
    item_data: str = ""
    item_type: str = ""
    item_amount: int = 0
    price: float = 0.0
    seller_uuid: str = ""
    seller_name: str = ""
    error: str | None = None


class AuctionService:
    def __init__(
        self,
        auction_repo: AuctionRepository,
        claims_repo: ClaimsRepository,
        listing_cache: ListingCache,
        economy_api: EconomyAPI,
        item_serializer: ItemSerializer,
        config: dict[str, Any],
        logger: Logger,
    ) -> None:
        self._auction_repo = auction_repo
        self._claims_repo = claims_repo
        self._cache = listing_cache
        self._economy_api = economy_api
        self._item_serializer = item_serializer
        self._config = config
        self._logger = logger

    @property
    def listing_tax_percent(self) -> float:
        return self._config.get("listing_tax_percent", 5.0)

    @property
    def max_active_listings(self) -> int:
        return self._config.get("max_active_listings", 28)

    @property
    def default_duration_hours(self) -> int:
        return self._config.get("default_listing_duration_hours", 48)

    @property
    def min_price(self) -> float:
        return self._config.get("min_listing_price", 1.0)

    @property
    def max_price(self) -> float:
        return self._config.get("max_listing_price", 1_000_000_000.0)

    @property
    def disabled_items(self) -> list[str]:
        return self._config.get("disabled_items", [])

    async def create_listing(
        self,
        seller_uuid: str,
        seller_name: str,
        item_type: str,
        item_amount: int,
        item_data: str,
        price: float,
        category: str | None = None,
    ) -> ListingResult:
        if item_type.lower() in [i.lower() for i in self.disabled_items]:
            return ListingResult(success=False, error="disabled_item")
        if price < self.min_price or price > self.max_price:
            return ListingResult(success=False, error="invalid_price")
        
        active_count = await self._auction_repo.get_seller_active_count(seller_uuid)
        if active_count >= self.max_active_listings:
            return ListingResult(success=False, error="max_listings")

        tax_rate = self.listing_tax_percent / 100.0
        tax_amount = round(price * tax_rate, 2)
        if tax_amount > 0:
            has_funds = await self._economy_api.has_balance(seller_uuid, tax_amount)
            if not has_funds:
                return ListingResult(success=False, error="insufficient_tax")
            await self._economy_api.remove_balance(seller_uuid, tax_amount)

        item_display = self._item_serializer.get_display_name(item_type)
        listing_id = await self._auction_repo.create_listing(
            seller_uuid=seller_uuid, seller_name=seller_name, item_data=item_data,
            item_type=item_type, item_display=item_display, item_amount=item_amount,
            price=price, category=category, duration_hours=self.default_duration_hours,
        )

        self._cache.invalidate_all()
        return ListingResult(success=True, listing_id=listing_id, tax_amount=tax_amount)

    async def purchase_listing(self, listing_id: int, buyer_uuid: str, buyer_name: str) -> PurchaseResult:
        listing = await self._auction_repo.purchase_listing(listing_id, buyer_uuid, buyer_name)
        if listing is None:
            return PurchaseResult(success=False, error="listing_unavailable")

        has_funds = await self._economy_api.has_balance(buyer_uuid, listing.price)
        if not has_funds:
            return PurchaseResult(success=False, error="insufficient_funds")
            
        remove_result = await self._economy_api.remove_balance(buyer_uuid, listing.price)
        if remove_result is None:
            return PurchaseResult(success=False, error="insufficient_funds")

        await self._economy_api.add_balance(listing.seller_uuid, listing.price)
        await self._claims_repo.create_claim(
            player_uuid=buyer_uuid, claim_type="PURCHASE", item_data=listing.item_data,
            item_type=listing.item_type, item_amount=listing.item_amount,
            source_id=listing.id, source_type="AUCTION",
        )

        self._cache.invalidate_all()
        return PurchaseResult(
            success=True, item_data=listing.item_data, item_type=listing.item_type,
            item_amount=listing.item_amount, price=listing.price,
            seller_uuid=listing.seller_uuid, seller_name=listing.seller_name,
        )

    async def get_active_listings(self, page: int = 1, per_page: int = 7, sort_by: str = "created_at") -> list:
        offset = (page - 1) * per_page
        cache_key = f"listings:{page}:{per_page}:{sort_by}"
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached
        listings = await self._auction_repo.get_active_listings(limit=per_page, offset=offset, sort_by=sort_by)
        self._cache.set(cache_key, listings)
        return listings

    async def get_listings_by_category(self, category: str, page: int = 1, per_page: int = 7) -> list:
        offset = (page - 1) * per_page
        return await self._auction_repo.get_listings_by_category(category, per_page, offset)

    async def get_expired_listings(self, seller_uuid: str) -> list:
        return await self._claims_repo.get_unclaimed(seller_uuid)

    async def reclaim_expired(self, player_uuid: str) -> int:
        return await self._claims_repo.mark_all_claimed(player_uuid)

    async def cancel_listing(self, listing_id: int, seller_uuid: str):
        result = await self._auction_repo.cancel_listing(listing_id, seller_uuid)
        if result:
            self._cache.invalidate_all()
        return result

    async def expire_listings(self) -> int:
        count = await self._auction_repo.expire_old_listings()
        if count > 0:
            self._cache.invalidate_all()
        return count

    async def get_active_count(self) -> int:
        return await self._auction_repo.get_active_count()
