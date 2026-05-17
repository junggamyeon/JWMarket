

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jwmarket.database.database_manager import DatabaseManager


@dataclass(frozen=True, slots=True)
class OrderRecord:
    id: int
    creator_uuid: str
    creator_name: str
    order_type: str
    item_type: str
    item_display: str
    quantity_total: int
    quantity_filled: int
    price_each: float
    escrow_amount: float
    category: str | None
    status: str
    created_at: str
    expires_at: str


class OrderRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def create_order(
        self,
        creator_uuid: str,
        creator_name: str,
        order_type: str,
        item_type: str,
        item_display: str,
        quantity: int,
        price_each: float,
        escrow_amount: float,
        category: str | None = None,
        duration_hours: int = 72,
    ) -> int:
        cursor = await self._db.execute(
            """
            INSERT INTO orders (creator_uuid, creator_name, order_type, item_type, item_display, quantity_total, quantity_filled, price_each, escrow_amount, category, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?, ?, datetime('now', '+' || ? || ' hours'))
            """,
            (creator_uuid, creator_name, order_type, item_type, item_display, quantity, price_each, escrow_amount, category, duration_hours),
        )
        return cursor.lastrowid

    async def get_player_active_count(self, creator_uuid: str) -> int:
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM orders WHERE creator_uuid = ? AND status = 'ACTIVE'",
            (creator_uuid,)
        ) or 0

    async def fulfill_order(
        self, order_id: int, fulfiller_uuid: str, fulfiller_name: str, quantity: int
    ) -> dict[str, Any] | None:
        async def _fulfill(cursor):
            await cursor.execute(
                "SELECT * FROM orders WHERE id = ? AND status = 'ACTIVE' AND expires_at > datetime('now')",
                (order_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            
            remaining = row["quantity_total"] - row["quantity_filled"]
            actual_fill = min(quantity, remaining)
            
            if actual_fill <= 0:
                return None
                
            new_filled = row["quantity_filled"] + actual_fill
            new_status = "FILLED" if new_filled >= row["quantity_total"] else "ACTIVE"
            total_payment = actual_fill * row["price_each"]
            
            await cursor.execute(
                "UPDATE orders SET quantity_filled = ?, status = ? WHERE id = ?",
                (new_filled, new_status, order_id)
            )
            
            await cursor.execute(
                """
                INSERT INTO order_history (order_id, fulfiller_uuid, fulfiller_name, quantity, total_payment)
                VALUES (?, ?, ?, ?, ?)
                """,
                (order_id, fulfiller_uuid, fulfiller_name, actual_fill, total_payment)
            )
            
            # Send items to the order creator via claims
            await cursor.execute(
                """
                INSERT INTO claims (player_uuid, claim_type, item_data, item_type, item_amount, source_id, source_type)
                VALUES (?, 'ORDER_FILLED', ?, ?, ?, ?, 'ORDER')
                """,
                (row["creator_uuid"], "{}", row["item_type"], actual_fill, order_id)
            )
            
            return {
                "actual_fill": actual_fill,
                "total_payment": total_payment,
                "new_filled": new_filled,
                "new_status": new_status,
                "total_quantity": row["quantity_total"],
                "item_type": row["item_type"],
                "creator_uuid": row["creator_uuid"],
                "creator_name": row["creator_name"],
            }

        return await self._db.execute_in_transaction(_fulfill)

    async def get_active_buy_orders(self, item_type: str | None = None, limit: int = 10, offset: int = 0) -> list[OrderRecord]:
        if item_type:
            query = "SELECT * FROM orders WHERE status = 'ACTIVE' AND order_type = 'BUY' AND item_type = ? AND expires_at > datetime('now') ORDER BY price_each DESC LIMIT ? OFFSET ?"
            params = (item_type, limit, offset)
        else:
            query = "SELECT * FROM orders WHERE status = 'ACTIVE' AND order_type = 'BUY' AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT ? OFFSET ?"
            params = (limit, offset)
            
        rows = await self._db.fetchall(query, params)
        return [self._map_row(r) for r in rows]

    async def browse_orders(self, category: str | None = None, limit: int = 10, offset: int = 0) -> list[OrderRecord]:
        if category:
            rows = await self._db.fetchall(
                "SELECT * FROM orders WHERE status = 'ACTIVE' AND category = ? AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (category, limit, offset)
            )
        else:
            rows = await self._db.fetchall(
                "SELECT * FROM orders WHERE status = 'ACTIVE' AND expires_at > datetime('now') ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (limit, offset)
            )
        return [self._map_row(r) for r in rows]

    async def get_player_orders(self, creator_uuid: str, status: str | None = None) -> list[OrderRecord]:
        if status:
            query = "SELECT * FROM orders WHERE creator_uuid = ? AND status = ? ORDER BY created_at DESC"
            params = (creator_uuid, status)
        else:
            query = "SELECT * FROM orders WHERE creator_uuid = ? ORDER BY created_at DESC"
            params = (creator_uuid,)
            
        rows = await self._db.fetchall(query, params)
        return [self._map_row(r) for r in rows]

    async def cancel_order(self, order_id: int, creator_uuid: str) -> OrderRecord | None:
        async def _cancel(cursor):
            await cursor.execute(
                "SELECT * FROM orders WHERE id = ? AND creator_uuid = ? AND status = 'ACTIVE'",
                (order_id, creator_uuid)
            )
            row = await cursor.fetchone()
            if not row:
                return None
                
            await cursor.execute("UPDATE orders SET status = 'CANCELLED' WHERE id = ?", (order_id,))
            return self._map_row(row)
            
        return await self._db.execute_in_transaction(_cancel)

    async def expire_old_orders(self) -> list[dict[str, Any]]:
        async def _expire(cursor):
            await cursor.execute(
                "SELECT id, creator_uuid, creator_name, quantity_total, quantity_filled, price_each FROM orders WHERE status = 'ACTIVE' AND expires_at <= datetime('now')"
            )
            expired = await cursor.fetchall()
            if not expired:
                return []
                
            results = []
            for row in expired:
                await cursor.execute("UPDATE orders SET status = 'EXPIRED' WHERE id = ?", (row["id"],))
                remaining = row["quantity_total"] - row["quantity_filled"]
                refund = remaining * row["price_each"]
                results.append({
                    "order_id": row["id"],
                    "creator_uuid": row["creator_uuid"],
                    "creator_name": row["creator_name"],
                    "refund_amount": refund
                })
            return results
            
        return await self._db.execute_in_transaction(_expire)

    async def get_order_by_id(self, order_id: int) -> OrderRecord | None:
        row = await self._db.fetchone("SELECT * FROM orders WHERE id = ?", (order_id,))
        return self._map_row(row) if row else None

    def _map_row(self, row: Any) -> OrderRecord:
        return OrderRecord(
            id=row["id"], creator_uuid=row["creator_uuid"], creator_name=row["creator_name"],
            order_type=row["order_type"], item_type=row["item_type"], item_display=row["item_display"],
            quantity_total=row["quantity_total"], quantity_filled=row["quantity_filled"],
            price_each=row["price_each"], escrow_amount=row["escrow_amount"], category=row["category"] if "category" in row.keys() else None,
            status=row["status"], created_at=row["created_at"], expires_at=row["expires_at"]
        )
