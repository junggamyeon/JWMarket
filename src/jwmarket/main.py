

from __future__ import annotations

import asyncio
import os
import threading
from typing import TYPE_CHECKING, Any

from endstone.plugin import Plugin
from endstone.command import Command, CommandSender

from jweconomy.api.economy_api import EconomyAPI

from jwmarket.cache.listing_cache import ListingCache
from jwmarket.cache.search_cache import SearchCache
from jwmarket.commands.ah_command import AuctionHouseCommandHandler
from jwmarket.commands.orders_command import OrdersCommandHandler
from jwmarket.database.database_manager import DatabaseManager
from jwmarket.database.repositories.auction_repository import AuctionRepository
from jwmarket.database.repositories.claims_repository import ClaimsRepository
from jwmarket.database.repositories.order_repository import OrderRepository
from jwmarket.database.schema import SchemaManager
from jwmarket.gui.gui_manager import GuiManager
from jwmarket.listeners.player_listener import MarketPlayerListener
from jwmarket.services.auction_service import AuctionService
from jwmarket.services.order_service import OrderService
from jwmarket.services.search_service import SearchService
from jwmarket.util.config_loader import ConfigLoader
from jwmarket.util.item_serializer import ItemSerializer
from jwmarket.util.message_formatter import MessageFormatter

if TYPE_CHECKING:
    from concurrent.futures import Future


class JWMarket(Plugin):


    api_version = "0.11"
    prefix = "§d§l[JWMarket]§r"
    version = "1.0.0"
    description = "Modern auction house and market system with SQLite backend."
    authors = ["JWDev"]
    depend = ["jweconomy"]

    commands = {
        "ah": {
            "description": "Auction House main command",
            "usages": [
                "/ah",
                "/ah sell <price: float>",
                "/ah search <keyword: string>",
                "/ah expired",
                "/ah orders",
                "/ah reload",
            ],
        },
        "orders": {
            "description": "Buy Orders main command",
            "usages": [
                "/orders",
                "/orders create",
                "/orders browse",
                "/orders fulfill",
            ],
        },
    }

    permissions = {
        "jwmarket.admin": {
            "description": "Allows reloading market config",
            "default": "op",
        },
    }

    def on_load(self) -> None:
        self._async_loop: asyncio.AbstractEventLoop | None = None
        self._async_thread: threading.Thread | None = None

        self._config_loader = ConfigLoader(self.data_folder, self.logger)
        self._config_loader.load_all()
        self._message_formatter = MessageFormatter(self._config_loader.messages)
        self._item_serializer = ItemSerializer()

        db_path = os.path.join(self.data_folder, self._config_loader.database_config.get("filename", "jwmarket.db"))
        self._db_manager = DatabaseManager(db_path, self.logger)

        self._start_async_loop()

    def on_enable(self) -> None:
        # Resolve JWEconomy API
        eco_plugin = self.server.plugin_manager.get_plugin("jweconomy")
        if not eco_plugin or not eco_plugin.is_enabled:
            self.logger.error("JWEconomy not found or not enabled. Please ensure JWEconomy is installed.")
            self.server.plugin_manager.disable_plugin(self)
            return
        
        self._economy_api = eco_plugin.economy_api

        future = self.run_async(self._initialize_database())
        try:
            future.result(timeout=10.0)
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            self.server.plugin_manager.disable_plugin(self)
            return

        self._auction_repo = AuctionRepository(self._db_manager)
        self._claims_repo = ClaimsRepository(self._db_manager)
        self._order_repo = OrderRepository(self._db_manager)

        self._listing_cache = ListingCache()
        self._search_cache = SearchCache()

        self._auction_service = AuctionService(
            self._auction_repo, self._claims_repo, self._listing_cache,
            self._economy_api, self._item_serializer, self._config_loader.market_config, self.logger
        )
        self._search_service = SearchService(
            self._auction_repo, self._search_cache, self._config_loader.categories, self.logger
        )
        self._order_service = OrderService(
            self._order_repo, self._economy_api, self._search_service, self._config_loader.market_config, self.logger
        )

        self._gui_manager = GuiManager(self)

        self._cmd_ah = AuctionHouseCommandHandler(self)
        self._cmd_orders = OrdersCommandHandler(self)

        self.register_events(MarketPlayerListener(self))

        # Expiry task every 5 minutes
        self.server.scheduler.run_task(self, self._run_expiry_tasks, delay=6000, period=6000)

    def on_disable(self) -> None:
        future = self.run_async(self._db_manager.close())
        try:
            future.result(timeout=5.0)
        except Exception as e:
            self.logger.error(f"Error closing database: {e}")

        self._stop_async_loop()

    def on_command(self, sender: CommandSender, command: Command, args: list[str]) -> bool:
        cmd_name = command.name.lower()
        if cmd_name == "ah":
            return self._cmd_ah.handle(sender, args)
        elif cmd_name == "orders":
            return self._cmd_orders.handle(sender, args)
        return False

    def run_async(self, coro: Any) -> Future:
        if self._async_loop is None or not self._async_loop.is_running():
            raise RuntimeError("Async loop is not running")
        return asyncio.run_coroutine_threadsafe(coro, self._async_loop)

    def _start_async_loop(self) -> None:
        def loop_runner():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._async_loop = loop
            loop.run_forever()
            loop.close()

        self._async_thread = threading.Thread(target=loop_runner, name="JWMarketAsyncThread", daemon=True)
        self._async_thread.start()

    def _stop_async_loop(self) -> None:
        if self._async_loop and self._async_loop.is_running():
            self._async_loop.call_soon_threadsafe(self._async_loop.stop)
        if self._async_thread:
            self._async_thread.join(timeout=5.0)

    async def _initialize_database(self) -> None:
        await self._db_manager.connect()
        schema_manager = SchemaManager(self._db_manager, self.logger)
        await schema_manager.create_tables()

    def _run_expiry_tasks(self) -> None:
        if hasattr(self, "_auction_service"):
            self.run_async(self._auction_service.expire_listings())
        if hasattr(self, "_order_service"):
            self.run_async(self._order_service.expire_orders())

    @property
    def economy_api(self) -> EconomyAPI:
        return self._economy_api

    @property
    def auction_service(self) -> AuctionService:
        return self._auction_service

    @property
    def order_service(self) -> OrderService:
        return self._order_service

    @property
    def search_service(self) -> SearchService:
        return self._search_service

    @property
    def claims_repo(self) -> ClaimsRepository:
        return self._claims_repo

    @property
    def gui_manager(self) -> GuiManager:
        return self._gui_manager

    @property
    def message_formatter(self) -> MessageFormatter:
        return self._message_formatter

    @property
    def item_serializer(self) -> ItemSerializer:
        return self._item_serializer
