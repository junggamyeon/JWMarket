

from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from jwmarket.main import JWMarket


class AuctionHouseCommandHandler:
    def __init__(self, plugin: JWMarket) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if len(args) == 0:
            if not isinstance(sender, Player):
                sender.send_message(self._plugin.message_formatter.format("player_only"))
                return True
            self._open_main_gui(sender)
            return True

        sub = args[0].lower()
        sub_args = args[1:]

        if sub == "sell":
            self._handle_sell(sender, sub_args)
        elif sub == "search":
            self._handle_search(sender, sub_args)
        elif sub == "expired":
            self._handle_expired(sender)
        elif sub == "orders":
            self._handle_my_orders(sender)
        elif sub == "reload":
            self._handle_reload(sender)
        else:
            self._show_usage(sender)

        return True

    def _open_main_gui(self, player: Player) -> None:
        try:
            self._plugin.gui_manager.show_main_menu(player)
        except Exception as e:
            self._plugin.logger.error(f"Error opening AH GUI: {e}")
            player.send_message(self._plugin.message_formatter.format("error_generic"))

    def _handle_sell(self, sender: CommandSender, args: list[str]) -> None:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.message_formatter.format("player_only"))
            return

        if len(args) < 1:
            sender.send_message(self._plugin.message_formatter.format("usage_error", usage="/ah sell <price>"))
            return

        try:
            price = float(args[0])
        except ValueError:
            sender.send_message(self._plugin.message_formatter.format("ah_invalid_price", min=self._plugin.auction_service.min_price, max=self._plugin.auction_service.max_price))
            return

        if price <= 0:
            sender.send_message(self._plugin.message_formatter.format("ah_invalid_price", min=self._plugin.auction_service.min_price, max=self._plugin.auction_service.max_price))
            return

        inventory = sender.inventory
        item = inventory.item_in_main_hand
        if item is None:
            sender.send_message(self._plugin.message_formatter.format("ah_no_item_hand"))
            return

        # Endstone item.type is an ItemType object, get the string representation
        item_type_obj = item.type
        item_type = getattr(item_type_obj, "id", getattr(item_type_obj, "name", str(item_type_obj)))
        
        if item_type == "minecraft:air":
            sender.send_message(self._plugin.message_formatter.format("ah_no_item_hand"))
            return
        
        item_amount = item.amount
        item_aux_data = item.data if item.data else 0
        item_nbt = item.nbt  # CompoundTag or None
        serializer = self._plugin.item_serializer
        item_data = serializer.serialize(item_type, item_amount, data=item_aux_data, nbt=item_nbt)
        category = self._plugin.search_service.find_category_for_item(item_type)

        player_uuid = str(sender.unique_id)
        player_name = sender.name

        async def task():
            try:
                result = await self._plugin.auction_service.create_listing(
                    seller_uuid=player_uuid, seller_name=player_name, item_type=item_type,
                    item_amount=item_amount, item_data=item_data, price=price, category=category,
                )
                def callback():
                    if not result.success:
                        error_key = {
                            "disabled_item": "ah_disabled_item",
                            "invalid_price": "ah_invalid_price",
                            "max_listings": "ah_max_listings",
                            "insufficient_tax": "ah_insufficient_funds",
                        }.get(result.error, "error_generic")

                        if error_key == "ah_invalid_price":
                            sender.send_message(self._plugin.message_formatter.format(error_key, min=self._plugin.auction_service.min_price, max=self._plugin.auction_service.max_price))
                        elif error_key == "ah_max_listings":
                            sender.send_message(self._plugin.message_formatter.format(error_key, max=self._plugin.auction_service.max_active_listings))
                        else:
                            sender.send_message(self._plugin.message_formatter.format(error_key))
                        return

                    inventory.item_in_main_hand = None
                    symbol = self._plugin.economy_api.currency_symbol
                    formatted_price = self._plugin.message_formatter.format_price(price, symbol)
                    item_display = serializer.get_display_name(item_type)

                    sender.send_message(self._plugin.message_formatter.format("ah_listed", item_name=item_display, amount=item_amount, price=formatted_price))
                    if result.tax_amount > 0:
                        formatted_tax = self._plugin.message_formatter.format_price(result.tax_amount, symbol)
                        sender.send_message(self._plugin.message_formatter.format("ah_listing_tax", tax_amount=formatted_tax, tax_percent=self._plugin.auction_service.listing_tax_percent))
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error creating listing: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: sender.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _handle_search(self, sender: CommandSender, args: list[str]) -> None:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.message_formatter.format("player_only"))
            return
        if len(args) < 1:
            sender.send_message(self._plugin.message_formatter.format("usage_error", usage="/ah search <keyword>"))
            return
        keyword = " ".join(args)
        self._plugin.gui_manager.show_search_results(sender, keyword)

    def _handle_expired(self, sender: CommandSender) -> None:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.message_formatter.format("player_only"))
            return
        player_uuid = str(sender.unique_id)
        async def task():
            try:
                claims = await self._plugin.auction_service.get_expired_listings(player_uuid)
                def callback():
                    if not claims:
                        sender.send_message(self._plugin.message_formatter.format("ah_no_expired"))
                        return
                    self._plugin.gui_manager.show_expired_items(sender, claims)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error getting expired listings: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: sender.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _handle_my_orders(self, sender: CommandSender) -> None:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.message_formatter.format("player_only"))
            return
        self._plugin.gui_manager.show_my_listings(sender)

    def _handle_reload(self, sender: CommandSender) -> None:
        if not sender.is_op:
            sender.send_message(self._plugin.message_formatter.format("no_permission"))
            return
        try:
            self._plugin._config_loader.reload()
            self._plugin._message_formatter.reload(self._plugin._config_loader.messages)
            sender.send_message(self._plugin.message_formatter.format("ah_reload"))
        except Exception as e:
            self._plugin.logger.error(f"Error reloading market config: {e}")
            sender.send_message(self._plugin.message_formatter.format("error_generic"))

    def _show_usage(self, sender: CommandSender) -> None:
        sender.send_message("§d§l--- JWMarket ---§r")
        sender.send_message("§e/ah §7- Browse the Auction House")
        sender.send_message("§e/ah sell <price> §7- List held item")
        sender.send_message("§e/ah search <keyword> §7- Search listings")
        sender.send_message("§e/ah expired §7- Reclaim expired items")
        sender.send_message("§e/ah orders §7- Your active listings")
        sender.send_message("§e/ah reload §7- Reload config (admin)")
