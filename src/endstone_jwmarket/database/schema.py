

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from endstone import Logger
    from jwmarket.database.database_manager import DatabaseManager


class SchemaManager:


    def __init__(self, db: DatabaseManager, logger: Logger) -> None:
        self._db = db
        self._logger = logger

    async def create_tables(self) -> None:
        await self._create_auctions_table()
        await self._create_orders_table()
        await self._create_claims_table()
        await self._create_history_table()

    async def _create_auctions_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS auctions (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                seller_uuid     TEXT NOT NULL,
                seller_name     TEXT NOT NULL,
                item_data       TEXT NOT NULL,
                item_type       TEXT NOT NULL,
                item_display    TEXT NOT NULL,
                item_amount     INTEGER NOT NULL,
                price           REAL NOT NULL,
                category        TEXT,
                status          TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at      TEXT NOT NULL
            );
        """)

    async def _create_orders_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS orders (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_uuid    TEXT NOT NULL,
                creator_name    TEXT NOT NULL,
                order_type      TEXT NOT NULL,
                item_type       TEXT NOT NULL,
                item_display    TEXT NOT NULL,
                quantity_total  INTEGER NOT NULL,
                quantity_filled INTEGER NOT NULL DEFAULT 0,
                price_each      REAL NOT NULL,
                escrow_amount   REAL NOT NULL DEFAULT 0.0,
                status          TEXT NOT NULL DEFAULT 'ACTIVE',
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at      TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS order_fills (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id        INTEGER NOT NULL,
                fulfiller_uuid  TEXT NOT NULL,
                fulfiller_name  TEXT NOT NULL,
                quantity        INTEGER NOT NULL,
                price_paid      REAL NOT NULL,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                FOREIGN KEY (order_id) REFERENCES orders(id)
            );
        """)

    async def _create_claims_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS claims (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                player_uuid     TEXT NOT NULL,
                claim_type      TEXT NOT NULL,
                item_data       TEXT NOT NULL,
                item_type       TEXT NOT NULL,
                item_amount     INTEGER NOT NULL,
                source_id       INTEGER NOT NULL,
                source_type     TEXT NOT NULL,
                is_claimed      INTEGER NOT NULL DEFAULT 0,
                created_at      TEXT NOT NULL DEFAULT (datetime('now')),
                claimed_at      TEXT
            );
        """)

    async def _create_history_table(self) -> None:
        await self._db.executescript("""
            CREATE TABLE IF NOT EXISTS listing_history (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                listing_id      INTEGER NOT NULL,
                buyer_uuid      TEXT NOT NULL,
                buyer_name      TEXT NOT NULL,
                price           REAL NOT NULL,
                purchased_at    TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
