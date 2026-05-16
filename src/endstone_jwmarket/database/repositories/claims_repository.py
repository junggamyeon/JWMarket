

from __future__ import annotations

from typing import Any

from jwmarket.database.database_manager import DatabaseManager


class ClaimsRepository:
    def __init__(self, db: DatabaseManager) -> None:
        self._db = db

    async def create_claim(
        self,
        player_uuid: str,
        claim_type: str,
        item_data: str,
        item_type: str,
        item_amount: int,
        source_id: int,
        source_type: str,
    ) -> int:
        cursor = await self._db.execute(
            """
            INSERT INTO claims (player_uuid, claim_type, item_data, item_type, item_amount, source_id, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (player_uuid, claim_type, item_data, item_type, item_amount, source_id, source_type),
        )
        return cursor.lastrowid

    async def get_unclaimed(self, player_uuid: str) -> list[dict[str, Any]]:
        rows = await self._db.fetchall(
            """
            SELECT * FROM claims
            WHERE player_uuid = ? AND is_claimed = 0
            ORDER BY created_at DESC
            """,
            (player_uuid,),
        )
        return [dict(r) for r in rows]

    async def get_unclaimed_count(self, player_uuid: str) -> int:
        return await self._db.fetchval(
            "SELECT COUNT(*) FROM claims WHERE player_uuid = ? AND is_claimed = 0",
            (player_uuid,),
        ) or 0

    async def mark_claimed(self, claim_id: int) -> bool:
        cursor = await self._db.execute(
            "UPDATE claims SET is_claimed = 1, claimed_at = datetime('now') WHERE id = ? AND is_claimed = 0",
            (claim_id,),
        )
        return cursor.rowcount > 0

    async def mark_all_claimed(self, player_uuid: str) -> int:
        cursor = await self._db.execute(
            "UPDATE claims SET is_claimed = 1, claimed_at = datetime('now') WHERE player_uuid = ? AND is_claimed = 0",
            (player_uuid,),
        )
        return cursor.rowcount
