

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from endstone import Logger

_DEFAULT_CONFIG = {
    "database": {
        "filename": "jwmarket.db",
    },
    "market": {
        "listing_tax_percent": 5.0,
        "order_tax_percent": 2.0,
        "max_active_listings": 28,
        "max_active_orders": 10,
        "default_listing_duration_hours": 48,
        "default_order_duration_hours": 72,
        "min_listing_price": 1.0,
        "max_listing_price": 1_000_000_000.0,
        "disabled_items": [
            "minecraft:bedrock",
            "minecraft:barrier",
            "minecraft:command_block"
        ]
    },
}

_DEFAULT_MESSAGES = {
    "prefix": "[JWMarket] ",
    "ah_listed": "{prefix}Successfully listed {item_name} x{amount} for {price}.",
    "ah_listing_tax": "{prefix}Listing tax paid: {tax_amount} ({tax_percent}%)",
    "ah_disabled_item": "{prefix}You cannot list this item on the market.",
    "ah_invalid_price": "{prefix}Price must be between {min} and {max}.",
    "ah_max_listings": "{prefix}You have reached the maximum of {max} active listings.",
    "ah_insufficient_funds": "{prefix}You do not have enough money for this.",
    "ah_purchased": "{prefix}You purchased {item_name} x{amount} for {price}.",
    "ah_sold_notification": "{prefix}Your listing for {item_name} x{amount} was sold for {price}!",
    "ah_listing_removed": "{prefix}Listing cancelled and item moved to your expired items.",
    "ah_search_results": "{prefix}Found {count} results for '{keyword}'.",
    "ah_search_empty": "{prefix}No listings found for '{keyword}'.",
    "ah_expired_item": "{prefix}You have {count} expired/cancelled item(s). Use /ah expired to reclaim them.",
    "ah_no_expired": "{prefix}You have no expired items.",
    "ah_reclaimed": "{prefix}Successfully reclaimed {count} item(s).",
    "ah_no_item_hand": "{prefix}You must hold an item in your main hand to list it.",
    "order_created": "{prefix}Buy order created for {item_name} x{amount} at {price_each}/each.",
    "order_escrow": "{prefix}Escrow placed: {escrow_amount}",
    "order_max_reached": "{prefix}You have reached the maximum of {max} active buy orders.",
    "order_fulfilled": "{prefix}You fulfilled {amount}x {item_name} and received {payment}.",
    "order_partial": "{prefix}(Filled {filled} out of {total} requested)",
    "order_cancelled": "{prefix}Order cancelled. Refunded {refund} to your balance.",
    "ah_reload": "{prefix}Configuration reloaded.",
    "no_permission": "{prefix}You do not have permission to do that.",
    "player_only": "{prefix}This command can only be used by players.",
    "usage_error": "{prefix}Usage: {usage}",
    "error_generic": "{prefix}An internal error occurred. Please try again later.",

    "gui_main_menu_title": "JWMarket",
    "gui_main_menu_content": "Explore the Black Market\nSelect a category:",
    "gui_btn_all_listings": "All Items",
    "gui_btn_search": "Search",
    "gui_btn_my_listings": "My Listings",
    "gui_btn_orders": "Buy Orders",
    "gui_btn_expired": "Expired",
    "gui_btn_back": "Back",
    "gui_btn_next_page": "Next Page",
    "gui_btn_prev_page": "Previous Page",

    "gui_ah_title": "Black Market",
    "gui_ah_page_title": "Black Market - Page {page}",
    "gui_ah_empty": "No items are listed.",
    "gui_ah_content": "Select an item to view details:",

    "gui_cat_title": "{category} - Page {page}",
    "gui_cat_empty": "No items in this category.",
    "gui_cat_content": "Items in this category:",

    "gui_listing_detail_title": "Item Details",
    "gui_listing_detail_content": "{item_name} x{amount}\nPrice: {price}\nSeller: {seller}\nCategory: {category}",
    "gui_btn_buy": "Buy for {price}",
    "gui_btn_cancel_listing": "Cancel Listing",
    "gui_listing_unavailable": "This item is no longer available.",

    "gui_search_title": "Black Market Search",
    "gui_search_label": "Search keyword (e.g. diamond):",
    "gui_search_placeholder": "enter keyword...",
    "gui_search_result_title": "Search: {keyword}",
    "gui_search_result_content": "Found {count} results:",

    "gui_my_listings_title": "My Listings",
    "gui_my_listings_content": "You have {count} active listings:",

    "gui_expired_title": "Expired Items",
    "gui_expired_content": "You have {count} expired items to reclaim:",
    "gui_btn_reclaim_all": "Reclaim All ({count} items)",

    "gui_my_orders_title": "My Buy Orders",
    "gui_my_orders_content": "You have {count} active buy orders:",
    "gui_btn_create_order": "Create New Buy Order",

    "gui_order_detail_title": "Buy Order Details",
    "gui_order_detail_content": "Buy Order #{id}\nItem: {item_name}\nPrice per item: {price}\nProgress: {filled}/{total}\nEscrow: {escrow}\nStatus: {status}",
    "gui_btn_cancel_order": "Cancel Buy Order",
    "gui_order_not_found": "Buy order not found.",

    "gui_create_order_title": "Create Buy Order",
    "gui_create_order_item_label": "Item type (e.g. minecraft:diamond):",
    "gui_create_order_qty_label": "Quantity:",
    "gui_create_order_price_label": "Price per item:",
    "gui_create_order_empty_fields": "Please fill in all fields.",
    "gui_create_order_invalid_values": "Invalid quantity or price. Please enter positive numbers.",

    "gui_fulfill_order_title": "Sell Items",
    "gui_fulfill_order_content": "Buy Order #{id}\nNeed: {item_name} x{remaining}\nPrice: {price}/each\nBuyer: {buyer}",
    "gui_btn_fulfill": "Sell Items",
    "gui_fulfill_must_hold": "You must hold the required item in your hand to sell.",
    "gui_fulfill_failed": "Failed to fulfill this buy order."
}

_DEFAULT_CATEGORIES = {
    "blocks": {
        "display_name": "Blocks",
        "icon": "textures/blocks/grass_side_carried",
        "items": [
            "minecraft:dirt", "minecraft:stone", "minecraft:cobblestone",
            "minecraft:oak_log", "minecraft:glass", "minecraft:diamond_block"
        ]
    },
    "tools": {
        "display_name": "Tools & Weapons",
        "icon": "textures/items/diamond_sword",
        "items": [
            "minecraft:wooden_sword", "minecraft:iron_pickaxe", "minecraft:diamond_sword",
            "minecraft:bow", "minecraft:trident"
        ]
    },
    "misc": {
        "display_name": "Miscellaneous",
        "icon": "textures/items/apple",
        "items": []
    }
}


class ConfigLoader:
    def __init__(self, data_folder: Path, logger: Logger) -> None:
        self._data_folder = data_folder
        self._logger = logger
        self._config: dict[str, Any] = {}
        self._messages: dict[str, str] = {}
        self._categories: dict[str, Any] = {}

    @property
    def database_config(self) -> dict[str, Any]:
        return self._config.get("database", _DEFAULT_CONFIG["database"])

    @property
    def market_config(self) -> dict[str, Any]:
        return self._config.get("market", _DEFAULT_CONFIG["market"])

    @property
    def messages(self) -> dict[str, str]:
        return self._messages

    @property
    def categories(self) -> dict[str, Any]:
        return self._categories

    def load_all(self) -> None:
        self._data_folder.mkdir(parents=True, exist_ok=True)
        self._config = self._load_yaml("config.yml", _DEFAULT_CONFIG)
        self._messages = self._load_yaml("messages.yml", _DEFAULT_MESSAGES)
        self._categories = self._load_yaml("categories.yml", _DEFAULT_CATEGORIES)

    def reload(self) -> None:
        self.load_all()

    def _load_yaml(self, filename: str, defaults: dict) -> dict:
        filepath = self._data_folder / filename
        if not filepath.exists():
            self._save_yaml(filepath, defaults)
            return dict(defaults)
        try:
            with filepath.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                self._logger.warning(f"Invalid {filename}, using defaults.")
                return dict(defaults)
            return self._deep_merge(defaults, data)
        except Exception as e:
            self._logger.error(f"Error loading {filename}: {e}")
            return dict(defaults)

    def _save_yaml(self, filepath: Path, data: dict) -> None:
        try:
            with filepath.open("w", encoding="utf-8") as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        except Exception as e:
            self._logger.error(f"Error saving {filepath.name}: {e}")

    @staticmethod
    def _deep_merge(defaults: dict, overrides: dict) -> dict:
        result = dict(defaults)
        for key, value in overrides.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = ConfigLoader._deep_merge(result[key], value)
            else:
                result[key] = value
        return result
