"""Game core: level state and the simulation tic (35 Hz). Independent of graphics and sound.

Public surface: Game(defs, level, bus), game.tick(TicCommand), game.player, game.entities,
game.level, game.state ("playing" | "dead" | "exit"). Everything else goes through bus events (engine/events.py).
"""
from __future__ import annotations

import math
import random

from config import GRAVITY, PLAYER_HEIGHT, STEP_HEIGHT, TICRATE
from engine.events import EventBus
from entities.base import Entity, Pickup
from entities.monsters import Monster
from gameplay import combat, pickups, triggers
from gameplay.player import Player, TicCommand
from gameplay.sectors import SectorManager
from world.collision import has_line_of_sight, opening, position_valid, slide_move, blocking_line
from world.geometry import segments_intersect
from world.map_data import Level


class Game:
    def __init__(self, defs, level: Level, bus: EventBus | None = None, seed: int = 1,
                 carry: dict | None = None):
        self.defs, self.level = defs, level
        self.bus = bus or EventBus()
        self.rng = random.Random(seed)
        self.entities: list[Entity] = []
        self.sectors = SectorManager()
        self.tic = 0
        self.state = "playing"
        self.kills = self.items = self.secrets = 0
        self.total_kills = self.total_items = self.total_secrets = 0
        self.player: Player = None  # type: ignore[assignment]
        self._spawn_things(carry)
        self.total_secrets = sum(1 for s in level.sectors if s.secret)
        self.bus.emit("level_start", game=self)

    # --- creation -------------------------------------------------------------
    def _spawn_things(self, carry: dict | None) -> None:
        for t in self.level.things:
            sec = self.level.sector_at(t.x, t.y)
            if sec is None:
                raise ValueError(f"Thing {t.type} at ({t.x}, {t.y}) is outside any sector")
            if t.type == "player_start":
                if self.player is None:
                    self.player = Player(t.x, t.y, sec.floor, t.angle, self.defs)
                    if carry:
                        self.player.load_state(carry)
            elif t.type in self.defs.monsters:
                self.entities.append(Monster(self.defs.monsters[t.type], t.x, t.y, sec.floor, t.angle))
                self.total_kills += 1
            elif t.type in self.defs.pickups:
                p = Pickup(self.defs.pickups[t.type], t.x, t.y, sec.floor)
                self.entities.append(p)
                self.total_items += p.pdef.count_item
            else:
                raise ValueError(f"Unknown thing type '{t.type}'")
        self.entities.insert(0, self.player)
        self.player.floor_z = self.player.z

    def spawn_pickup(self, pickup_id: str, x: float, y: float) -> None:
        sec = self.level.sector_at(x, y)
        if sec is not None:
            self.entities.append(Pickup(self.defs.pickups[pickup_id], x, y, sec.floor))

    # --- events ---------------------------------------------------------
    def play_sound(self, name: str, x: float | None, y: float | None) -> None:
        self.bus.emit("sound", name=name, x=x, y=y)

    def message(self, text: str) -> None:
        self.bus.emit("message", text=text)

    def exit_level(self) -> None:
        if self.state == "playing":
            self.state = "exit"
            self.bus.emit("level_exit", game=self)

    def player_died(self) -> None:
        self.state = "dead"
        self.play_sound("player_death", None, None)

    # --- queries ---------------------------------------------------------------
    def has_los(self, a: Entity, b: Entity) -> bool:
        za = a.z + a.height * 0.75
        return has_line_of_sight(self.level, a.x, a.y, za, b.x, b.y, b.z + b.height * 0.5)

    def entities_in_sector(self, sector) -> list[Entity]:
        return [e for e in self.entities
                if e.solid and not e.removed and self.level.sector_at(e.x, e.y) is sector]

    def _blocked_by_entity(self, ent: Entity, nx: float, ny: float) -> bool:
        for e in self.entities:
            if e is ent or not e.solid or e.removed:
                continue
            if ent.z >= e.z + e.height or e.z >= ent.z + ent.height:
                continue
            reach = ent.radius + e.radius
            d_new = math.hypot(nx - e.x, ny - e.y)
            if d_new < reach and d_new < math.hypot(ent.x - e.x, ent.y - e.y):
                return True
        return False

    # --- movement -----------------------------------------------------------------
    def move_entity(self, ent: Entity, dx: float, dy: float) -> None:
        """Movement with wall sliding and blocking by other creatures."""
        dist = math.hypot(dx, dy)
        if dist < 1e-9:
            return
        n = max(1, math.ceil(dist / (ent.radius * 0.75)))
        sx, sy = dx / n, dy / n
        for _ in range(n):
            nx, ny = slide_move(self.level, ent.x, ent.y, sx, sy, ent.radius, ent.z, ent.height, STEP_HEIGHT)
            if self._blocked_by_entity(ent, nx, ny):
                for ax, ay in ((sx, 0.0), (0.0, sy)):
                    cx, cy = slide_move(self.level, ent.x, ent.y, ax, ay, ent.radius, ent.z, ent.height, STEP_HEIGHT)
                    if (cx, cy) != (ent.x, ent.y) and not self._blocked_by_entity(ent, cx, cy):
                        nx, ny = cx, cy
                        break
                else:
                    break
            if (nx, ny) == (ent.x, ent.y):
                break
            ent.x, ent.y = nx, ny
            self.update_z(ent)

    def try_step(self, ent: Entity, dx: float, dy: float) -> bool:
        """A monster step without sliding. If a keyless door is in the way, the monster opens it."""
        nx, ny = ent.x + dx, ent.y + dy
        if not position_valid(self.level, nx, ny, ent.radius, ent.z, ent.height, STEP_HEIGHT, STEP_HEIGHT):
            ln = blocking_line(self.level, nx, ny, ent.radius + 8, ent.z, ent.height, STEP_HEIGHT)
            if ln is not None and ln.special and ln.special["action"] == "door" and ln.special["trigger"] == "use" \
                    and not ln.special["key"]:
                triggers.activate_line(self, ln, ent, ent.x, ent.y)
            return False
        if self._blocked_by_entity(ent, nx, ny):
            return False
        ent.x, ent.y = nx, ny
        self.update_z(ent)
        return True

    def update_z(self, ent: Entity) -> None:
        """Floor under a creature and gravity (rising with a lift, falling off a ledge)."""
        fc = self.level.floor_ceiling_at(ent.x, ent.y, ent.radius, STEP_HEIGHT)
        if fc is None:
            return
        floor = fc[0]
        ent.floor_z = floor
        if ent.z < floor:
            ent.z, ent.vz = floor, 0.0
        elif ent.z > floor:
            ent.vz -= GRAVITY * (2 if ent.vz == 0 else 1)
            ent.z = max(floor, ent.z + ent.vz)
            if ent.z <= floor:
                ent.vz = 0.0
        else:
            ent.vz = 0.0

    # --- player actions ----------------------------------------------------------
    def use_pressed(self) -> None:
        triggers.use_line(self, self.player)

    def check_walk_triggers(self, ox: float, oy: float, nx: float, ny: float) -> None:
        if (ox, oy) == (nx, ny):
            return
        for ln in self.level.linedefs:
            sp = ln.special
            if sp and sp["trigger"] == "walk" and segments_intersect((ox, oy), (nx, ny), (ln.x1, ln.y1), (ln.x2, ln.y2)):
                triggers.activate_line(self, ln, self.player, nx, ny)

    def check_pickups(self) -> None:
        p = self.player
        for e in self.entities:
            if isinstance(e, Pickup) and not e.removed and \
                    math.hypot(e.x - p.x, e.y - p.y) < p.radius + e.radius and \
                    e.z < p.z + PLAYER_HEIGHT and p.z < e.z + e.height:
                pickups.try_pickup(self, p, e)

    def player_attack(self, wdef, accurate: bool) -> None:
        p = self.player
        if wdef.sound:
            self.play_sound(wdef.sound, None, None)
        if wdef.noisy:
            self.alert_monsters()
        rng_range = 64.0 if wdef.melee else wdef.range
        slope = combat.find_autoaim_slope(self, p, p.angle, rng_range)
        if wdef.projectile:
            combat.spawn_projectile(self, p, self.defs.projectiles[wdef.projectile], p.angle, slope)
        else:
            for _ in range(wdef.pellets):
                spread = 0.0 if accurate else wdef.spread_deg * (self.rng.random() - self.rng.random())
                combat.hitscan_attack(self, p, p.angle + spread, slope, wdef.damage, rng_range)
        self.bus.emit("weapon_fired", game=self, weapon=wdef.id)

    def alert_monsters(self) -> None:
        """A shot wakes monsters in connected open sectors (sound does not pass through closed doors)."""
        start = self.level.sector_at(self.player.x, self.player.y)
        if start is None:
            return
        reached, frontier = {start.id}, [start.id]
        while frontier:
            sid = frontier.pop()
            for ln in self.level.linedefs:
                if ln.back is None or sid not in (ln.front, ln.back):
                    continue
                other = ln.back if ln.front == sid else ln.front
                bottom, top = opening(self.level, ln)
                if other not in reached and top - bottom > 0:
                    reached.add(other)
                    frontier.append(other)
        for e in self.entities:
            if isinstance(e, Monster) and e.state == "idle":
                sec = self.level.sector_at(e.x, e.y)
                if sec is not None and sec.id in reached:
                    e.wake(self)

    # --- tic -----------------------------------------------------------------
    def tick(self, cmd: TicCommand) -> None:
        if self.state == "exit":
            return
        self.tic += 1
        for e in self.entities:
            e.save_prev()
        if self.player.alive:
            self.player.update(self, cmd)
        else:
            self.player.update_dead(self)
        for e in list(self.entities):
            if e is not self.player and not e.removed:
                e.tick(self)
        self.sectors.tick(self)
        self.entities = [e for e in self.entities if not e.removed]
        if self.player.alive:
            self._sector_effects()
        self.bus.emit("tick", game=self)

    def _sector_effects(self) -> None:
        p = self.player
        sec = self.level.sector_at(p.x, p.y)
        if sec is None:
            return
        if sec.secret:
            sec.secret = False
            self.secrets += 1
            self.message("You found a secret area!")
            self.play_sound("secret", None, None)
        if sec.damage and self.tic % 32 == 0 and p.z <= p.floor_z + 0.01:
            p.take_damage(self, sec.damage, None)

    @property
    def time_seconds(self) -> float:
        return self.tic / TICRATE
