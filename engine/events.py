"""Simple event bus. The game core only publishes events; graphics, sound and mods subscribe.

Core events (arguments are keyword-only):
  sound(name, x, y)            — play a sound (x, y = None for a "global" sound)
  message(text)                — message to the player
  tick(game)                   — end of every game tic
  level_start(game)            — level created
  weapon_fired(game, weapon)   — weapon id
  monster_killed(game, monster)
  pickup(game, pickup_id)
  player_damaged(game, amount)
  level_exit(game)
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

log = logging.getLogger("opendoom")


class EventBus:
    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable]] = defaultdict(list)

    def on(self, event: str, handler: Callable) -> None:
        self._handlers[event].append(handler)

    def emit(self, event: str, **data) -> None:
        for handler in list(self._handlers.get(event, ())):
            try:
                handler(**data)
            except Exception:  # an error in a mod handler must not crash the game
                log.exception("Error in handler for event %r", event)
