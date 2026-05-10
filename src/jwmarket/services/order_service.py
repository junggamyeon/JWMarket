

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from endstone import Logger
    from jweconomy.api.economy_api import EconomyAPI
    from jwmarket.database.repositories.order_repository import OrderRepository


@dataclass(frozen=True, slots=True)
class OrderCreateResult:
    success: bool
    order_id: int = 0
    escrow_amount: float = 0.0
    error: str | None = None


@dataclass(frozen=True, slots=True)
class OrderFulfillResult:
    success: bool
    quantity_filled: int = 0
    payment: float = 0.0
    remaining: int = 0
    order_complete: bool = False
    item_type: str = ""
    creator_uuid: str = ""
    creator_name: str = ""
    error: str | None = None


class OrderService:
    def __init__(self, order_repo: OrderRepository, economy_api: EconomyAPI, config: dict[str, Any], logger: Logger) -> None:
        self._order_repo = order_repo
        self._economy_api = economy_api
        self._config = config
        self._logger = logger

    @property
    def order_tax_percent(self) -> float:
        return self._config.get("order_tax_percent", 2.0)

    @property
    def max_active_orders(self) -> int:
        return self._config.get("max_active_orders", 10)

    @property
    def default_duration_hours(self) -> int:
        return self._config.get("default_order_duration_hours", 72)

    async def create_buy_order(self, creator_uuid: str, creator_name: str, item_type: str, quantity: int, price_each: float) -> OrderCreateResult:
        active_count = await self._order_repo.get_player_active_count(creator_uuid)
        if active_count >= self.max_active_orders:
            return OrderCreateResult(success=False, error="max_orders")

        escrow_amount = quantity * price_each
        has_funds = await self._economy_api.has_balance(creator_uuid, escrow_amount)
        if not has_funds:
            return OrderCreateResult(success=False, error="insufficient_funds")

        remove_result = await self._economy_api.remove_balance(creator_uuid, escrow_amount)
        if remove_result is None:
            return OrderCreateResult(success=False, error="insufficient_funds")

        from jwmarket.util.item_serializer import ItemSerializer
        serializer = ItemSerializer()
        item_display = serializer.get_display_name(item_type)

        order_id = await self._order_repo.create_order(
            creator_uuid=creator_uuid, creator_name=creator_name, order_type="BUY",
            item_type=item_type, item_display=item_display, quantity=quantity,
            price_each=price_each, escrow_amount=escrow_amount, duration_hours=self.default_duration_hours,
        )
        return OrderCreateResult(success=True, order_id=order_id, escrow_amount=escrow_amount)

    async def fulfill_buy_order(self, order_id: int, fulfiller_uuid: str, fulfiller_name: str, quantity: int) -> OrderFulfillResult:
        fill_result = await self._order_repo.fulfill_order(order_id, fulfiller_uuid, fulfiller_name, quantity)
        if fill_result is None:
            return OrderFulfillResult(success=False, error="order_unavailable")

        actual_fill = fill_result["actual_fill"]
        total_payment = fill_result["total_payment"]
        tax_rate = self.order_tax_percent / 100.0
        tax_amount = round(total_payment * tax_rate, 2)
        net_payment = total_payment - tax_amount

        await self._economy_api.add_balance(fulfiller_uuid, net_payment)

        return OrderFulfillResult(
            success=True, quantity_filled=actual_fill, payment=net_payment,
            remaining=fill_result["total_quantity"] - fill_result["new_filled"],
            order_complete=(fill_result["new_status"] == "FILLED"),
            item_type=fill_result.get("item_type", ""),
            creator_uuid=fill_result.get("creator_uuid", ""),
            creator_name=fill_result.get("creator_name", ""),
        )

    async def cancel_order(self, order_id: int, creator_uuid: str) -> dict[str, Any] | None:
        order = await self._order_repo.cancel_order(order_id, creator_uuid)
        if order is None:
            return None
        remaining = order.quantity_total - order.quantity_filled
        refund = remaining * order.price_each
        if refund > 0:
            await self._economy_api.add_balance(creator_uuid, refund)
        return {"refund": refund, "order": order}

    async def get_active_buy_orders(self, item_type: str | None = None, page: int = 1, per_page: int = 7) -> list:
        offset = (page - 1) * per_page
        return await self._order_repo.get_active_buy_orders(item_type, per_page, offset)

    async def browse_orders(self, page: int = 1, per_page: int = 7) -> list:
        offset = (page - 1) * per_page
        return await self._order_repo.browse_orders(per_page, offset)

    async def get_player_orders(self, creator_uuid: str, status: str | None = None) -> list:
        return await self._order_repo.get_player_orders(creator_uuid, status)

    async def expire_orders(self) -> int:
        expired_list = await self._order_repo.expire_old_orders()
        for entry in expired_list:
            refund = entry["refund_amount"]
            if refund > 0:
                try:
                    await self._economy_api.add_balance(entry["creator_uuid"], refund)
                except Exception as e:
                    self._logger.error(f"Failed to refund expired order: {e}")
        return len(expired_list)
