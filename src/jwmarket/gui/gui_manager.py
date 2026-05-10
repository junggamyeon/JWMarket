from __future__ import annotations

from typing import TYPE_CHECKING
import json

from endstone import Player
from endstone.form import ActionForm, ModalForm, Dropdown, TextInput, Label
from endstone.inventory import ItemStack

if TYPE_CHECKING:
    from jwmarket.main import JWMarket


class GuiManager:

    def __init__(self, plugin: JWMarket) -> None:
        self._plugin = plugin

    def _create_item_from_data(self, item_data_json: str, override_amount: int | None = None) -> ItemStack:
        parsed = self._plugin.item_serializer.deserialize(item_data_json)
        item_type = parsed["type"]
        amount = override_amount if override_amount is not None else parsed["amount"]
        data = parsed.get("data", 0)
        item_stack = ItemStack(item_type, amount, data)
        nbt = parsed.get("nbt")
        if nbt is not None:
            item_stack.nbt = nbt
        return item_stack

    def show_main_menu(self, player: Player) -> None:
        form = ActionForm(
            title=self._plugin.message_formatter.format("gui_main_menu_title"),
            content=self._plugin.message_formatter.format("gui_main_menu_content"),
        )
        categories = self._plugin.search_service.get_category_list()
        form.add_button(self._plugin.message_formatter.format("gui_btn_all_listings"), icon="textures/items/emerald", on_click=lambda p: self._show_all_listings(p))
        for cat in categories:
            form.add_button(
                cat["display_name"],
                icon=cat["icon"] if cat["icon"] else None,
                on_click=lambda p, c=cat["key"]: self._show_category_listings(p, c),
            )
        form.add_button(self._plugin.message_formatter.format("gui_btn_search"), icon="textures/items/compass_item", on_click=lambda p: self._show_search_form(p))
        form.add_button(self._plugin.message_formatter.format("gui_btn_my_listings"), on_click=lambda p: self.show_my_listings(p))
        form.add_button(self._plugin.message_formatter.format("gui_btn_orders"), on_click=lambda p: self.show_my_orders(p))
        form.add_button(self._plugin.message_formatter.format("gui_btn_expired"), on_click=lambda p: self._show_expired_gui(p))
        player.send_form(form)

    def _show_all_listings(self, player: Player, page: int = 1) -> None:
        async def task():
            try:
                listings = await self._plugin.auction_service.get_active_listings(page=page)
                def callback():
                    if not listings:
                        form = ActionForm(title=self._plugin.message_formatter.format("gui_ah_title"), content=self._plugin.message_formatter.format("gui_ah_empty"))
                        form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                        player.send_form(form)
                        return

                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_ah_page_title", page=page), content=self._plugin.message_formatter.format("gui_ah_content"))
                    for listing in listings:
                        price_str = self._plugin.message_formatter.format_price(listing.price, sym)
                        btn_text = f"§e{listing.item_display} §7x{listing.item_amount}\n§a{price_str} §8- {listing.seller_name}"
                        form.add_button(btn_text, on_click=lambda p, lid=listing.id: self._show_listing_detail(p, lid))
                    if len(listings) >= 7:
                        form.add_button(self._plugin.message_formatter.format("gui_btn_next_page"), on_click=lambda p: self._show_all_listings(p, page + 1))
                    if page > 1:
                        form.add_button(self._plugin.message_formatter.format("gui_btn_prev_page"), on_click=lambda p: self._show_all_listings(p, page - 1))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading listings: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _show_category_listings(self, player: Player, category: str, page: int = 1) -> None:
        async def task():
            try:
                listings = await self._plugin.auction_service.get_listings_by_category(category, page=page)
                def callback():
                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_cat_title", category=category.title(), page=page), content=self._plugin.message_formatter.format("gui_cat_content"))
                    if not listings:
                        form = ActionForm(title=self._plugin.message_formatter.format("gui_cat_title", category=category.title(), page=page), content=self._plugin.message_formatter.format("gui_cat_empty"))
                        form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                        player.send_form(form)
                        return

                    for listing in listings:
                        price_str = self._plugin.message_formatter.format_price(listing.price, sym)
                        btn_text = f"§e{listing.item_display} §7x{listing.item_amount}\n§a{price_str}"
                        form.add_button(btn_text, on_click=lambda p, lid=listing.id: self._show_listing_detail(p, lid))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading category: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _show_listing_detail(self, player: Player, listing_id: int) -> None:
        async def task():
            try:
                listing = await self._plugin.auction_service._auction_repo.get_listing_by_id(listing_id)
                def callback():
                    if listing is None or listing.status != "ACTIVE":
                        player.send_message(self._plugin.message_formatter.format("gui_listing_unavailable"))
                        return

                    sym = self._plugin.economy_api.currency_symbol
                    price_str = self._plugin.message_formatter.format_price(listing.price, sym)
                    content = self._plugin.message_formatter.format(
                        "gui_listing_detail_content",
                        item_name=listing.item_display,
                        amount=listing.item_amount,
                        price=price_str,
                        seller=listing.seller_name,
                        category=listing.category or "None"
                    )

                    form = ActionForm(title=self._plugin.message_formatter.format("gui_listing_detail_title"), content=content)
                    player_uuid = str(player.unique_id)
                    if player_uuid != listing.seller_uuid:
                        form.add_button(self._plugin.message_formatter.format("gui_btn_buy", price=price_str), on_click=lambda p: self._confirm_purchase(p, listing_id))
                    else:
                        form.add_button(self._plugin.message_formatter.format("gui_btn_cancel_listing"), on_click=lambda p: self._cancel_listing(p, listing_id))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self._show_all_listings(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading listing detail: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _confirm_purchase(self, player: Player, listing_id: int) -> None:
        buyer_uuid = str(player.unique_id)
        buyer_name = player.name
        async def task():
            try:
                result = await self._plugin.auction_service.purchase_listing(listing_id, buyer_uuid, buyer_name)
                def callback():
                    if not result.success:
                        error_map = {
                            "listing_unavailable": self._plugin.message_formatter.format("gui_listing_unavailable"),
                            "insufficient_funds": self._plugin.message_formatter.format("ah_insufficient_funds"),
                        }
                        player.send_message(error_map.get(result.error, self._plugin.message_formatter.format("error_generic")))
                        return

                    try:
                        item_stack = self._create_item_from_data(result.item_data, override_amount=result.item_amount)
                        player.inventory.add_item(item_stack)
                    except Exception as e:
                        self._plugin.logger.error(f"Error giving purchased item to buyer: {e}")

                    sym = self._plugin.economy_api.currency_symbol
                    price_str = self._plugin.message_formatter.format_price(result.price, sym)
                    item_display = self._plugin.item_serializer.get_display_name(result.item_type)

                    player.send_message(self._plugin.message_formatter.format("ah_purchased", item_name=item_display, amount=result.item_amount, price=price_str))

                    seller = self._plugin.server.get_player(result.seller_name)
                    if seller:
                        seller.send_message(self._plugin.message_formatter.format("ah_sold_notification", item_name=item_display, amount=result.item_amount, price=price_str))
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error purchasing listing: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _cancel_listing(self, player: Player, listing_id: int) -> None:
        player_uuid = str(player.unique_id)
        async def task():
            try:
                result = await self._plugin.auction_service.cancel_listing(listing_id, player_uuid)
                def callback():
                    if result:
                        player.send_message(self._plugin.message_formatter.format("ah_listing_removed"))
                    else:
                        player.send_message("§cCould not cancel this listing.")
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error cancelling listing: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _show_search_form(self, player: Player) -> None:
        form = ModalForm(title=self._plugin.message_formatter.format("gui_search_title"))
        form.add_control(TextInput(label=self._plugin.message_formatter.format("gui_search_label"), placeholder=self._plugin.message_formatter.format("gui_search_placeholder")))
        
        def handle_submit(p, d):
            if isinstance(d, str):
                try:
                    d = json.loads(d)
                except Exception:
                    pass
            self.show_search_results(p, d[0] if d and isinstance(d, list) else "")
            
        form.on_submit = handle_submit
        player.send_form(form)

    def show_search_results(self, player: Player, keyword: str, page: int = 1) -> None:
        if not keyword.strip():
            player.send_message(self._plugin.message_formatter.format("usage_error", usage="/ah search <keyword>"))
            return
        async def task():
            try:
                results, count = await self._plugin.search_service.search(keyword, page=page)
                def callback():
                    if not results:
                        player.send_message(self._plugin.message_formatter.format("ah_search_empty", keyword=keyword))
                        return

                    player.send_message(self._plugin.message_formatter.format("ah_search_results", keyword=keyword, count=count))
                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_search_result_title", keyword=keyword), content=self._plugin.message_formatter.format("gui_search_result_content", count=count))
                    for listing in results:
                        price_str = self._plugin.message_formatter.format_price(listing.price, sym)
                        btn = f"§e{listing.item_display} §7x{listing.item_amount}\n§a{price_str} §8- {listing.seller_name}"
                        form.add_button(btn, on_click=lambda p, lid=listing.id: self._show_listing_detail(p, lid))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error searching: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_my_listings(self, player: Player) -> None:
        player_uuid = str(player.unique_id)
        async def task():
            try:
                listings = await self._plugin.auction_service._auction_repo.get_seller_listings(player_uuid, "ACTIVE")
                def callback():
                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_my_listings_title"), content=self._plugin.message_formatter.format("gui_my_listings_content", count=len(listings)))
                    for listing in listings:
                        price_str = self._plugin.message_formatter.format_price(listing.price, sym)
                        btn = f"§e{listing.item_display} §7x{listing.item_amount}\n§a{price_str}"
                        form.add_button(btn, on_click=lambda p, lid=listing.id: self._show_listing_detail(p, lid))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading my listings: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_expired_items(self, player: Player, claims: list) -> None:
        form = ActionForm(title=self._plugin.message_formatter.format("gui_expired_title"), content=self._plugin.message_formatter.format("gui_expired_content", count=len(claims)))
        form.add_button(self._plugin.message_formatter.format("gui_btn_reclaim_all", count=len(claims)), on_click=lambda p, c=claims: self._reclaim_all(p, c))
        form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
        player.send_form(form)

    def _show_expired_gui(self, player: Player) -> None:
        player_uuid = str(player.unique_id)
        async def task():
            try:
                claims = await self._plugin.auction_service.get_expired_listings(player_uuid)
                def callback():
                    if not claims:
                        player.send_message(self._plugin.message_formatter.format("ah_no_expired"))
                        return
                    self.show_expired_items(player, claims)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading expired: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _reclaim_all(self, player: Player, claims: list) -> None:
        player_uuid = str(player.unique_id)
        if not claims:
            return

        items_given = 0
        for claim in claims:
            try:
                item_data_json = claim.get("item_data", "")
                if item_data_json:
                    item_stack = self._create_item_from_data(item_data_json, override_amount=claim["item_amount"])
                else:
                    item_stack = ItemStack(claim["item_type"], claim["item_amount"])
                player.inventory.add_item(item_stack)
                items_given += 1
            except Exception as e:
                self._plugin.logger.error(f"Error giving item {claim.get('item_type')}: {e}")

        async def task():
            try:
                await self._plugin.auction_service.reclaim_expired(player_uuid)
                def callback():
                    player.send_message(self._plugin.message_formatter.format("ah_reclaimed", count=items_given))
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error reclaiming: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_my_orders(self, player: Player) -> None:
        player_uuid = str(player.unique_id)
        async def task():
            try:
                orders = await self._plugin.order_service.get_player_orders(player_uuid, "ACTIVE")
                def callback():
                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_my_orders_title"), content=self._plugin.message_formatter.format("gui_my_orders_content", count=len(orders)))
                    for order in orders:
                        price_str = self._plugin.message_formatter.format_price(order.price_each, sym)
                        filled = f"{order.quantity_filled}/{order.quantity_total}"
                        btn = f"§e{order.item_display}\n§7{filled} - §a{price_str}"
                        form.add_button(btn, on_click=lambda p, oid=order.id: self._show_order_detail(p, oid))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_create_order"), on_click=lambda p: self.show_create_order_form(p))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading orders: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _show_order_detail(self, player: Player, order_id: int) -> None:
        async def task():
            try:
                order = await self._plugin.order_service._order_repo.get_order_by_id(order_id)
                def callback():
                    if order is None:
                        player.send_message(self._plugin.message_formatter.format("gui_order_not_found"))
                        return

                    sym = self._plugin.economy_api.currency_symbol
                    price_str = self._plugin.message_formatter.format_price(order.price_each, sym)
                    escrow_str = self._plugin.message_formatter.format_price(order.escrow_amount, sym)
                    content = self._plugin.message_formatter.format(
                        "gui_order_detail_content",
                        id=order.id,
                        item_name=order.item_display,
                        price=price_str,
                        filled=order.quantity_filled,
                        total=order.quantity_total,
                        escrow=escrow_str,
                        status=order.status
                    )
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_order_detail_title"), content=content)
                    player_uuid = str(player.unique_id)
                    if order.creator_uuid == player_uuid and order.status == "ACTIVE":
                        form.add_button(self._plugin.message_formatter.format("gui_btn_cancel_order"), on_click=lambda p: self._cancel_order(p, order_id))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_my_orders(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error loading order: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _cancel_order(self, player: Player, order_id: int) -> None:
        player_uuid = str(player.unique_id)
        async def task():
            try:
                result = await self._plugin.order_service.cancel_order(order_id, player_uuid)
                def callback():
                    if result:
                        sym = self._plugin.economy_api.currency_symbol
                        refund_str = self._plugin.message_formatter.format_price(result["refund"], sym)
                        player.send_message(self._plugin.message_formatter.format("order_cancelled", refund=refund_str))
                    else:
                        player.send_message("§cCould not cancel this order.")
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error cancelling order: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_create_order_form(self, player: Player) -> None:
        form = ModalForm(title=self._plugin.message_formatter.format("gui_create_order_title"))
        form.add_control(TextInput(label=self._plugin.message_formatter.format("gui_create_order_item_label"), placeholder="minecraft:diamond"))
        form.add_control(TextInput(label=self._plugin.message_formatter.format("gui_create_order_qty_label"), placeholder="64"))
        form.add_control(TextInput(label=self._plugin.message_formatter.format("gui_create_order_price_label"), placeholder="10"))
        form.on_submit = lambda p, data: self._process_create_order(p, data)
        player.send_form(form)

    def _process_create_order(self, player: Player, data) -> None:
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except Exception:
                pass
                
        if not data or not isinstance(data, list) or len(data) < 3:
            player.send_message(self._plugin.message_formatter.format("error_generic"))
            return
            
        item_type = str(data[0]).strip() if data[0] is not None else ""
        qty_str = str(data[1]).strip() if len(data) > 1 and data[1] is not None else ""
        price_str = str(data[2]).strip() if len(data) > 2 and data[2] is not None else ""
        
        if not item_type or not qty_str or not price_str:
            player.send_message(self._plugin.message_formatter.format("gui_create_order_empty_fields"))
            return
            
        try:
            quantity = int(qty_str)
            price_each = float(price_str)
        except (ValueError, TypeError):
            player.send_message(self._plugin.message_formatter.format("gui_create_order_invalid_values"))
            return
        if quantity <= 0 or price_each <= 0 or not item_type:
            player.send_message(self._plugin.message_formatter.format("gui_create_order_invalid_values"))
            return

        player_uuid = str(player.unique_id)
        player_name = player.name
        async def task():
            try:
                result = await self._plugin.order_service.create_buy_order(player_uuid, player_name, item_type, quantity, price_each)
                def callback():
                    if not result.success:
                        error_map = {
                            "max_orders": self._plugin.message_formatter.format("order_max_reached", max=self._plugin.order_service.max_active_orders),
                            "insufficient_funds": self._plugin.message_formatter.format("ah_insufficient_funds"),
                        }
                        player.send_message(error_map.get(result.error, self._plugin.message_formatter.format("error_generic")))
                        return

                    sym = self._plugin.economy_api.currency_symbol
                    price_str = self._plugin.message_formatter.format_price(price_each, sym)
                    escrow_str = self._plugin.message_formatter.format_price(result.escrow_amount, sym)
                    item_display = self._plugin.item_serializer.get_display_name(item_type)
                    player.send_message(self._plugin.message_formatter.format("order_created", item_name=item_display, amount=quantity, price_each=price_str))
                    player.send_message(self._plugin.message_formatter.format("order_escrow", escrow_amount=escrow_str))
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error creating order: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_browse_orders(self, player: Player, page: int = 1) -> None:
        async def task():
            try:
                orders = await self._plugin.order_service.browse_orders(page=page)
                def callback():
                    sym = self._plugin.economy_api.currency_symbol
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_my_orders_title"), content=f"§7Active buy orders (page {page}):")
                    if not orders:
                        form = ActionForm(title=self._plugin.message_formatter.format("gui_my_orders_title"), content=self._plugin.message_formatter.format("gui_ah_empty"))
                        form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                        player.send_form(form)
                        return
                    for order in orders:
                        price_str = self._plugin.message_formatter.format_price(order.price_each, sym)
                        remaining = order.quantity_total - order.quantity_filled
                        btn = f"§e{order.item_display} §7x{remaining}\n§a{price_str}/ea §8- {order.creator_name}"
                        form.add_button(btn, on_click=lambda p, oid=order.id: self._show_fulfill_detail(p, oid))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_main_menu(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error browsing orders: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def show_fulfillable_orders(self, player: Player) -> None:
        self.show_browse_orders(player)

    def _show_fulfill_detail(self, player: Player, order_id: int) -> None:
        async def task():
            try:
                order = await self._plugin.order_service._order_repo.get_order_by_id(order_id)
                def callback():
                    if not order or order.status != "ACTIVE":
                        player.send_message(self._plugin.message_formatter.format("gui_order_not_found"))
                        return

                    sym = self._plugin.economy_api.currency_symbol
                    remaining = order.quantity_total - order.quantity_filled
                    price_str = self._plugin.message_formatter.format_price(order.price_each, sym)
                    content = self._plugin.message_formatter.format(
                        "gui_fulfill_order_content",
                        id=order.id,
                        item_name=order.item_display,
                        remaining=remaining,
                        price=price_str,
                        buyer=order.creator_name
                    )
                    form = ActionForm(title=self._plugin.message_formatter.format("gui_fulfill_order_title"), content=content)
                    form.add_button(self._plugin.message_formatter.format("gui_btn_fulfill"), on_click=lambda p: self._fulfill_order_prompt(p, order_id, remaining))
                    form.add_button(self._plugin.message_formatter.format("gui_btn_back"), on_click=lambda p: self.show_browse_orders(p))
                    player.send_form(form)
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())

    def _fulfill_order_prompt(self, player: Player, order_id: int, max_qty: int) -> None:
        inventory = player.inventory
        item = inventory.item_in_main_hand
        
        if item is None:
            player.send_message(self._plugin.message_formatter.format("gui_fulfill_must_hold"))
            return
            
        item_type_obj = item.type
        item_type_str = getattr(item_type_obj, "id", getattr(item_type_obj, "name", str(item_type_obj)))
        
        if item_type_str == "minecraft:air":
            player.send_message(self._plugin.message_formatter.format("gui_fulfill_must_hold"))
            return

        available = min(item.amount, max_qty)
        fulfiller_uuid = str(player.unique_id)
        fulfiller_name = player.name
        async def task():
            try:
                result = await self._plugin.order_service.fulfill_buy_order(order_id, fulfiller_uuid, fulfiller_name, available)
                def callback():
                    if not result.success:
                        player.send_message(self._plugin.message_formatter.format("gui_fulfill_failed"))
                        return

                    new_amount = item.amount - result.quantity_filled
                    if new_amount <= 0:
                        inventory.item_in_main_hand = None
                    else:
                        item.amount = new_amount
                        inventory.item_in_main_hand = item

                    if result.creator_name:
                        order_creator = self._plugin.server.get_player(result.creator_name)
                        if order_creator:
                            try:
                                order_item = ItemStack(result.item_type, result.quantity_filled)
                                order_creator.inventory.add_item(order_item)
                                item_display = self._plugin.item_serializer.get_display_name(result.item_type)
                                order_creator.send_message(f"§a§l[JWMarket]§r §7Your order for §e{item_display} §7x{result.quantity_filled} has been fulfilled!")
                            except Exception as e:
                                self._plugin.logger.error(f"Error giving order items to creator: {e}")

                    sym = self._plugin.economy_api.currency_symbol
                    payment_str = self._plugin.message_formatter.format_price(result.payment, sym)
                    player.send_message(self._plugin.message_formatter.format(
                        "order_fulfilled", amount=result.quantity_filled, item_name="item", payment=payment_str,
                    ))
                    if not result.order_complete:
                        player.send_message(self._plugin.message_formatter.format(
                            "order_partial", filled=result.quantity_filled, total=result.quantity_filled + result.remaining,
                        ))
                self._plugin.server.scheduler.run_task(self._plugin, callback)
            except Exception as e:
                self._plugin.logger.error(f"Error fulfilling: {e}")
                self._plugin.server.scheduler.run_task(self._plugin, lambda: player.send_message(self._plugin.message_formatter.format("error_generic")))
        self._plugin.run_async(task())
