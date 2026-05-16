

from __future__ import annotations

from typing import TYPE_CHECKING

from endstone import Player
from endstone.command import CommandSender

if TYPE_CHECKING:
    from endstone_jwmarket.main import JWMarket


class OrdersCommandHandler:
    def __init__(self, plugin: JWMarket) -> None:
        self._plugin = plugin

    def handle(self, sender: CommandSender, args: list[str]) -> bool:
        if not isinstance(sender, Player):
            sender.send_message(self._plugin.message_formatter.format("player_only"))
            return True

        if len(args) == 0:
            self._plugin.gui_manager.show_my_orders(sender)
            return True

        sub = args[0].lower()
        if sub == "create":
            self._plugin.gui_manager.show_create_order_form(sender)
        elif sub == "browse":
            self._plugin.gui_manager.show_browse_orders(sender)
        elif sub == "fulfill":
            self._plugin.gui_manager.show_fulfillable_orders(sender)
        else:
            self._show_usage(sender)

        return True

    def _show_usage(self, sender: CommandSender) -> None:
        sender.send_message("§d§l--- JWMarket Orders ---§r")
        sender.send_message("§e/orders §7- View your orders")
        sender.send_message("§e/orders create §7- Create a buy order")
        sender.send_message("§e/orders browse §7- Browse all orders")
        sender.send_message("§e/orders fulfill §7- Fulfill an order")
