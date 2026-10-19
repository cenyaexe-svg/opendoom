"""Projectiles (imp fireballs, mod plasma...). Parameters live in the projectiles definitions."""
from __future__ import annotations

import math

from entities.base import Effect, Entity
from world.collision import trace_ray
from world.geometry import ray_circle


class Projectile(Entity):
    kind = "projectile"

    def __init__(self, pdef, owner: Entity, x, y, z, angle: float, slope: float):
        super().__init__(x, y, z, radius=pdef.radius, height=2 * pdef.radius, angle=angle)
        self.pdef, self.owner = pdef, owner
        self.sprite, self.fullbright, self.tint = pdef.sprite, True, pdef.tint
        self.dx, self.dy = math.cos(math.radians(angle)), math.sin(math.radians(angle))
        self.slope = slope

    def tick(self, game) -> None:
        speed, level = self.pdef.speed, game.level
        wall_t, wall_line = trace_ray(level, self.x, self.y, self.z, self.dx, self.dy, self.slope, speed)
        hit_t, hit_e = wall_t, None
        for e in game.entities:
            if e is self.owner or e.removed or not e.shootable or e.kind == self.owner.kind:
                continue
            if self.owner is not game.player and e is not game.player:
                continue                                  # monster projectiles hurt only the player
            t = ray_circle(self.x, self.y, self.dx, self.dy, e.x, e.y, e.radius + self.radius)
            if t is None or t >= hit_t:
                continue
            if e.z - self.radius <= self.z + self.slope * t <= e.z + e.height + self.radius:
                hit_t, hit_e = t, e
        if hit_e is not None or wall_line is not None:
            self.x, self.y, self.z = self.x + self.dx * hit_t, self.y + self.dy * hit_t, self.z + self.slope * hit_t
            self.explode(game, hit_e)
            return
        self.x += self.dx * speed
        self.y += self.dy * speed
        self.z += self.slope * speed
        sec = level.sector_at(self.x, self.y)
        if sec is None or self.z - self.radius < sec.floor or self.z + self.radius > sec.ceiling:
            self.explode(game, None)

    def explode(self, game, target: Entity | None) -> None:
        self.removed = True
        if target is not None:
            target.take_damage(game, self.pdef.damage.roll(game.rng), self.owner)
        game.entities.append(Effect(self.x, self.y, self.z - self.radius, self.pdef.explosion_sprite, 12,
                                    fullbright=True, tint=self.pdef.tint))
        if self.pdef.sound_hit:
            game.play_sound(self.pdef.sound_hit, self.x, self.y)
