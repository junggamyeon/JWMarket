from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from jwmarket.database.database_manager import DatabaseManager


@dataclass(frozen=True, slots=True)
class AuctionRecord:
    id: int
    seller_uuid: str
    seller_name: str
    item_data: str
    item_type: str
    item_display: str
    item_amount: int
    price: float
    category: str | None
    status: str
    created_at: str
    expires_at: str


class AuctionRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def create_listing(
        self,
        seller_uuid: str,
        seller_name: str,
        item_data: str,
        item_type: str,
        item_display: str,
        item_amount: int,
        price: float,
        category: str | None = None,
        duration_hours: int = 48,
    ) -> int:
        cursor = await self._db.execute(
            """
            INSERT INTO auctions (seller_uuid, seller_name, item_data, item_type, item_display, item_amount, price, category, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now', '+' || ? || ' hours'))
            """,
            (seller_uuid, seller_name, item_data, item_type, item_display, item_amount, price, category, duration_hours),
        )
        return cursor.lastrowid

    async def get_seller_active_count(self, seller_uuid: str) -> int:
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM auctions WHERE seller_uuid = ? AND status = 'ACTIVE'",
            (seller_uuid,)
        ) or 0

    async def get_seller_listings(self, seller_uuid: str, status: str) -> list[AuctionRecord]:
        query = """
            SELECT * FROM auctions
            WHERE seller_uuid = ? AND status = ?
            ORDER BY created_at DESC
        """
        rows = await self._db.fetchall(query, (seller_uuid, status))
        return [self._map_row(r) for r in rows]

    async def get_active_listings(self, limit: int = 10, offset: int = 0, sort_by: str = "created_at") -> list[AuctionRecord]:
        sort_clause = "created_at DESC" if sort_by == "created_at" else "price ASC"
        query = f"""
            SELECT * FROM auctions
            WHERE status = 'ACTIVE' AND expires_at > datetime('now')
            ORDER BY {sort_clause}
            LIMIT ? OFFSET ?
        """
        rows = await self._db.fetchall(query, (limit, offset))
        return [self._map_row(r) for r in rows]

    async def search_listings(self, keyword: str, limit: int = 10, offset: int = 0) -> list[AuctionRecord]:
        query = """
            SELECT * FROM auctions
            WHERE status = 'ACTIVE' AND expires_at > datetime('now')
              AND item_display LIKE ? COLLATE NOCASE
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = await self._db.fetchall(query, (f"%{keyword}%", limit, offset))
        return [self._map_row(r) for r in rows]

    async def search_count(self, keyword: str) -> int:
        query = """
            SELECT COUNT(*) FROM auctions
            WHERE status = 'ACTIVE' AND expires_at > datetime('now')
              AND item_display LIKE ? COLLATE NOCASE
        """
        return await self._db.fetchval(query, (f"%{keyword}%",)) or 0

    async def get_listings_by_category(self, category: str, limit: int = 10, offset: int = 0) -> list[AuctionRecord]:
        query = """
            SELECT * FROM auctions
            WHERE status = 'ACTIVE' AND expires_at > datetime('now') AND category = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        rows = await self._db.fetchall(query, (category, limit, offset))
        return [self._map_row(r) for r in rows]

    async def purchase_listing(self, listing_id: int, buyer_uuid: str, buyer_name: str) -> AuctionRecord | None:
        async def _purchase(cursor):
            await cursor.execute("SELECT * FROM auctions WHERE id = ? AND status = 'ACTIVE'", (listing_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            await cursor.execute("UPDATE auctions SET status = 'SOLD' WHERE id = ?", (listing_id,))
            await cursor.execute(
                """
                INSERT INTO listing_history (listing_id, buyer_uuid, buyer_name, price)
                VALUES (?, ?, ?, ?)
                """,
                (listing_id, buyer_uuid, buyer_name, row["price"])
            )
            return self._map_row(row)
        return await self._db.execute_in_transaction(_purchase)

    async def cancel_listing(self, listing_id: int, seller_uuid: str) -> bool:
        async def _cancel(cursor):
            await cursor.execute("SELECT * FROM auctions WHERE id = ? AND seller_uuid = ? AND status = 'ACTIVE'", (listing_id, seller_uuid))
            row = await cursor.fetchone()
            if not row:
                return False
            await cursor.execute("UPDATE auctions SET status = 'CANCELLED' WHERE id = ?", (listing_id,))
            await cursor.execute(
                """
                INSERT INTO claims (player_uuid, claim_type, item_data, item_type, item_amount, source_id, source_type)
                VALUES (?, 'CANCELLED', ?, ?, ?, ?, 'AUCTION')
                """,
                (row["seller_uuid"], row["item_data"], row["item_type"], row["item_amount"], row["id"])
            )
            return True
        return await self._db.execute_in_transaction(_cancel)

    async def expire_old_listings(self) -> int:
        async def _expire(cursor):
            await cursor.execute("SELECT * FROM auctions WHERE status = 'ACTIVE' AND expires_at <= datetime('now')")
            expired = await cursor.fetchall()
            if not expired:
                return 0
            
            for row in expired:
                await cursor.execute("UPDATE auctions SET status = 'EXPIRED' WHERE id = ?", (row["id"],))
                await cursor.execute(
                    """
                    INSERT INTO claims (player_uuid, claim_type, item_data, item_type, item_amount, source_id, source_type)
                    VALUES (?, 'EXPIRED', ?, ?, ?, ?, 'AUCTION')
                    """,
                    (row["seller_uuid"], row["item_data"], row["item_type"], row["item_amount"], row["id"])
                )
            return len(expired)
        return await self._db.execute_in_transaction(_expire)

    async def get_listing_by_id(self, listing_id: int) -> AuctionRecord | None:
        row = await self._db.fetchone("SELECT * FROM auctions WHERE id = ?", (listing_id,))
        return self._map_row(row) if row else None

    async def get_active_count(self) -> int:
        return await self._db.fetchval("SELECT COUNT(*) FROM auctions WHERE status = 'ACTIVE'") or 0

    def _map_row(self, row: Any) -> AuctionRecord:
        return AuctionRecord(
            id=row["id"], seller_uuid=row["seller_uuid"], seller_name=row["seller_name"],
            item_data=row["item_data"], item_type=row["item_type"], item_display=row["item_display"],
            item_amount=row["item_amount"], price=row["price"], category=row["category"],
            status=row["status"], created_at=row["created_at"], expires_at=row["expires_at"]
        )
