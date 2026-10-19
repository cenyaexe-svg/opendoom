"""Base entities: common ancestor, visual effect, pickup."""
from __future__ import annotations

import math


class Entity:
    """World object. z is the feet height. Graphics read only x, y, z, sprite, fullbright, tint."""
    kind = "entity"

    def __init__(self, x: float, y: float, z: float = 0.0, radius: float = 16.0,
                 height: float = 56.0, angle: float = 0.0):
        self.x, self.y, self.z = x, y, z
        self.prev_x, self.prev_y, self.prev_z = x, y, z
        self.radius, self.height, self.angle = radius, height, angle
        self.vz = 0.0
        self.floor_z = z
        self.solid = False          # blocks other creatures
        self.shootable = False      # bullets can hit it
        self.removed = False
        self.sprite = ""            # current sprite name
        self.fullbright = False     # not darkened by sector lighting
        self.tint: tuple[float, float, float] | None = None

    def save_prev(self) -> None:
        self.prev_x, self.prev_y, self.prev_z = self.x, self.y, self.z

    def distance_to(self, other: "Entity") -> float:
        return math.hypot(other.x - self.x, other.y - self.y)

    def tick(self, game) -> None:
        pass

    def take_damage(self, game, amount: int, source: "Entity | None") -> None:
        pass


class Effect(Entity):
    """Short-lived visual effect (hit, blood, explosion)."""
    kind = "effect"

    def __init__(self, x, y, z, sprite: str, ttl: int, fullbright: bool = False, tint=None):
        super().__init__(x, y, z, 0, 0)
        self.sprite, self.ttl, self.fullbright, self.tint = sprite, ttl, fullbright, tint

    def tick(self, game) -> None:
        self.ttl -= 1
        if self.ttl <= 0:
            self.removed = True


class Pickup(Entity):
    kind = "pickup"

    def __init__(self, pdef, x: float, y: float, z: float = 0.0):
        super().__init__(x, y, z, radius=20.0, height=16.0)
        self.pdef = pdef
        self.sprite = pdef.sprite
