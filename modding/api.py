"""Python API for script mods (script.py -> def register(api)).

    def register(api):
        api.on("monster_killed", lambda game, monster: api.message("Another one down!"))
        api.register_pickup_type("poison", handler)   # handler(game, player, pickup_def) -> bool (whether it was picked up)

Available events are listed in engine/events.py. Scripts have full Python access:
enable only mods you trust.
"""
from __future__ import annotations

from typing import Callable

from engine.events import EventBus
from gameplay import pickups


class ModAPI:
    def __init__(self, bus: EventBus, defs):
        self.bus = bus
        self.defs = defs                  # read-only by convention

    def on(self, event: str, handler: Callable) -> None:
        self.bus.on(event, handler)

    def message(self, text: str) -> None:
        self.bus.emit("message", text=text)

    def register_pickup_type(self, type_name: str, handler: Callable) -> None:
        pickups.HANDLERS[type_name] = handler
