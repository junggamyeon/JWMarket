

from typing import TYPE_CHECKING

from endstone.event import PlayerJoinEvent, event_handler

if TYPE_CHECKING:
    from endstone_jwmarket.main import JWMarket


class MarketPlayerListener:
    def __init__(self, plugin: 'JWMarket') -> None:
        self._plugin = plugin

    @event_handler
    def on_player_join(self, event: PlayerJoinEvent) -> None:
        player = event.player
        uuid = str(player.unique_id)

        # We wait 3 seconds to ensure the player is fully spawned in
        self._plugin.server.scheduler.run_task(
            self._plugin, 
            lambda: self._check_claims(player, uuid), 
            delay=60
        )

    def _check_claims(self, player, uuid: str) -> None:
        try:
            future = self._plugin.run_async(self._plugin.claims_repo.get_unclaimed_count(uuid))
            count = future.result(timeout=5.0)
            if count > 0:
                player.send_message(self._plugin.message_formatter.format("ah_expired_item", count=count))
        except Exception as e:
            self._plugin.logger.error(f"Error checking claims for {player.name}: {e}")
