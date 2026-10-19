"""Combat: hitscan, vertical auto-aim, projectile spawning."""
from __future__ import annotations

import math

from entities.base import Effect
from entities.projectiles import Projectile
from world.collision import trace_ray
from world.geometry import ray_circle

SHOT_HEIGHT = 32.0            # shot height above the floor (as in Doom)
AUTOAIM_SPREAD_DEG = 5.625
MAX_AUTOAIM_SLOPE = 0.625


def hitscan_attack(game, shooter, angle_deg: float, slope: float, dice, max_range: float):
    """Instant shot. Returns the entity that was hit, or None."""
    ox, oy, oz = shooter.x, shooter.y, shooter.z + SHOT_HEIGHT
    dx, dy = math.cos(math.radians(angle_deg)), math.sin(math.radians(angle_deg))
    wall_t, wall_line = trace_ray(game.level, ox, oy, oz, dx, dy, slope, max_range)
    best_t, best = wall_t, None
    for e in game.entities:
        if e is shooter or e.removed or not e.shootable:
            continue
        t = ray_circle(ox, oy, dx, dy, e.x, e.y, e.radius)
        if t is None or t >= best_t:
            continue
        if e.z <= oz + slope * t <= e.z + e.height:
            best_t, best = t, e
    px, py, pz = ox + dx * best_t, oy + dy * best_t, oz + slope * best_t
    if best is not None:
        best.take_damage(game, dice.roll(game.rng), shooter)
        game.entities.append(Effect(px, py, pz - 4, "blood", 10))
    elif wall_line is not None:
        game.entities.append(Effect(px - dx * 2, py - dy * 2, pz - 4, "puff", 8))
    return best


def find_autoaim_slope(game, shooter, angle_deg: float, max_range: float) -> float:
    """Vertical auto-aim: looks for a monster within a ±5.6° cone (like P_AimLineAttack)."""
    oz = shooter.z + SHOT_HEIGHT
    for off in (0.0, AUTOAIM_SPREAD_DEG, -AUTOAIM_SPREAD_DEG):
        a = math.radians(angle_deg + off)
        dx, dy = math.cos(a), math.sin(a)
        wall_t, _ = trace_ray(game.level, shooter.x, shooter.y, oz, dx, dy, 0.0, max_range)
        best_t, best = wall_t, None
        for e in game.entities:
            if e is shooter or e.removed or not e.shootable:
                continue
            t = ray_circle(shooter.x, shooter.y, dx, dy, e.x, e.y, e.radius)
            if t is not None and t < best_t:
                best_t, best = t, e
        if best is not None:
            slope = (best.z + best.height * 0.5 - oz) / max(best_t, 1.0)
            if abs(slope) <= MAX_AUTOAIM_SLOPE:
                return slope
    return 0.0


def slope_to(shooter, target) -> float:
    dist = max(1.0, shooter.distance_to(target))
    return (target.z + target.height * 0.5 - (shooter.z + SHOT_HEIGHT)) / dist


def spawn_projectile(game, owner, pdef, angle_deg: float, slope: float) -> Projectile:
    a = math.radians(angle_deg)
    off = owner.radius + pdef.radius
    p = Projectile(pdef, owner, owner.x + math.cos(a) * off, owner.y + math.sin(a) * off,
                   owner.z + SHOT_HEIGHT, angle_deg, slope)
    game.entities.append(p)
    if pdef.sound_launch:
        game.play_sound(pdef.sound_launch, owner.x, owner.y)
    return p
