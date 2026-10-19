"""Player: Doom-style movement (thrust/friction), inventory, armor, weapon states."""
from __future__ import annotations

import math
from dataclasses import dataclass

from config import (FRICTION, KEY_TURN_DEG, MAX_MOMENTUM, PLAYER_EYE, PLAYER_HEIGHT, PLAYER_RADIUS,
                    RUN_FORWARD, RUN_SIDE, STOP_SPEED, THRUST_DIV, WALK_FORWARD, WALK_SIDE, WEAPON_BOTTOM,
                    WEAPON_SWITCH_SPEED, WEAPON_TOP)
from entities.base import Entity


@dataclass
class TicCommand:
    """Player input for one tic. forward/strafe: -1..1, turn: degrees per tic."""
    forward: float = 0.0
    strafe: float = 0.0
    turn: float = 0.0
    fire: bool = False
    use: bool = False
    run: bool = True
    weapon: int | None = None        # slot number 1..9


class Player(Entity):
    kind = "player"

    def __init__(self, x: float, y: float, z: float, angle: float, defs):
        super().__init__(x, y, z, PLAYER_RADIUS, PLAYER_HEIGHT, angle)
        self.solid = self.shootable = True
        start = defs.settings.player_start
        self.health, self.armor, self.armor_type = start.health, start.armor, 1 if start.armor else 0
        self.ammo = dict(start.ammo)
        self.weapons = set(start.weapons)
        self.keys: set[str] = set()
        self.mx = self.my = 0.0
        self.bob = 0.0
        self.view_height = PLAYER_EYE
        self.damage_count = self.bonus_count = 0
        self.use_held = False
        self.refire = 0
        self.wstate, self.wtimer, self.flash = "raising", 0, 0
        self.wy = WEAPON_BOTTOM
        self.pending: str | None = None
        self.weapon = self.best_weapon(defs)

    # --- state -----------------------------------------------------------
    @property
    def alive(self) -> bool:
        return self.health > 0

    @property
    def eye_z(self) -> float:
        return self.z + self.view_height

    def has_ammo(self, wdef) -> bool:
        return wdef.ammo is None or self.ammo.get(wdef.ammo, 0) >= wdef.ammo_per_shot

    def best_weapon(self, defs) -> str:
        owned = sorted((defs.weapons[w] for w in self.weapons), key=lambda w: -w.slot)
        usable = [w for w in owned if self.has_ammo(w)]
        return (usable or owned)[0].id

    def save_state(self) -> dict:
        return {"health": self.health, "armor": self.armor, "armor_type": self.armor_type,
                "ammo": dict(self.ammo), "weapons": set(self.weapons), "weapon": self.weapon}

    def load_state(self, st: dict) -> None:
        self.health, self.armor, self.armor_type = max(st["health"], 1), st["armor"], st["armor_type"]
        self.ammo, self.weapons, self.weapon = dict(st["ammo"]), set(st["weapons"]), st["weapon"]

    # --- damage ------------------------------------------------------------
    def take_damage(self, game, amount: int, source) -> None:
        if not self.alive:
            return
        if self.armor_type:
            saved = amount // 3 if self.armor_type == 1 else amount // 2
            saved = min(saved, self.armor)
            self.armor -= saved
            if self.armor <= 0:
                self.armor_type = 0
            amount -= saved
        self.health -= amount
        self.damage_count = min(100, self.damage_count + amount)
        game.bus.emit("player_damaged", game=game, amount=amount)
        if self.health <= 0:
            self.health = min(self.health, 0)
            game.player_died()
        else:
            game.play_sound("player_pain", None, None)

    # --- tic ---------------------------------------------------------------
    def _thrust(self, angle_deg: float, amount: float) -> None:
        a = math.radians(angle_deg)
        self.mx += math.cos(a) * amount
        self.my += math.sin(a) * amount

    def update(self, game, cmd: TicCommand) -> None:
        self.damage_count = max(0, self.damage_count - 1)
        self.bonus_count = max(0, self.bonus_count - 1)
        ox, oy = self.x, self.y
        self.angle = (self.angle + cmd.turn) % 360
        if self.z <= self.floor_z + 0.01:
            fwd = (RUN_FORWARD if cmd.run else WALK_FORWARD) * cmd.forward
            side = (RUN_SIDE if cmd.run else WALK_SIDE) * cmd.strafe
            self._thrust(self.angle, fwd / THRUST_DIV)
            self._thrust(self.angle - 90, side / THRUST_DIV)
        speed = math.hypot(self.mx, self.my)
        if speed > MAX_MOMENTUM:
            self.mx, self.my = self.mx * MAX_MOMENTUM / speed, self.my * MAX_MOMENTUM / speed
        px, py = self.x, self.y
        game.move_entity(self, self.mx, self.my)
        self.mx, self.my = self.x - px, self.y - py      # as in Doom: momentum = the distance actually travelled
        game.update_z(self)
        if self.z <= self.floor_z + 0.01:
            self.mx *= FRICTION
            self.my *= FRICTION
            if abs(self.mx) < STOP_SPEED and abs(self.my) < STOP_SPEED and not cmd.forward and not cmd.strafe:
                self.mx = self.my = 0.0
        self.bob = min(16.0, (self.mx ** 2 + self.my ** 2) / 4)
        game.check_walk_triggers(ox, oy, self.x, self.y)
        game.check_pickups()
        if cmd.use and not self.use_held:
            game.use_pressed()
        self.use_held = cmd.use
        self._update_weapon(game, cmd)

    def update_dead(self, game) -> None:
        self.damage_count = max(0, self.damage_count - 1)
        self.view_height = max(6.0, self.view_height - 1.0)
        self.wy = min(WEAPON_BOTTOM, self.wy + WEAPON_SWITCH_SPEED)
        game.update_z(self)

    # --- weapon -----------------------------------------------------------
    def _update_weapon(self, game, cmd: TicCommand) -> None:
        defs = game.defs
        if cmd.weapon is not None:
            options = sorted((w for w in self.weapons if defs.weapons[w].slot == cmd.weapon and self.has_ammo(defs.weapons[w])),
                             key=lambda w: w)
            if options:
                nxt = options[(options.index(self.weapon) + 1) % len(options)] if self.weapon in options else options[0]
                if nxt != self.weapon and self.pending is None:
                    self.pending = nxt
        if self.flash > 0:
            self.flash -= 1
        if self.wstate == "lowering":
            self.wy += WEAPON_SWITCH_SPEED
            if self.wy >= WEAPON_BOTTOM:
                self.wy, self.weapon, self.pending, self.wstate = WEAPON_BOTTOM, self.pending or self.weapon, None, "raising"
        elif self.wstate == "raising":
            self.wy -= WEAPON_SWITCH_SPEED
            if self.wy <= WEAPON_TOP:
                self.wy, self.wstate = WEAPON_TOP, "ready"
        elif self.wstate == "firing":
            self.wtimer -= 1
            if self.wtimer <= 0:
                self.wstate = "ready"
        if self.wstate != "ready":
            return
        wdef = defs.weapons[self.weapon]
        if not self.has_ammo(wdef):
            self.pending = self.pending or self.best_weapon(defs)
        if self.pending and self.pending != self.weapon:
            self.wstate = "lowering"
        elif cmd.fire and self.has_ammo(wdef):
            accurate = wdef.accurate_first_shot and self.refire == 0
            self.refire += 1
            self.wstate, self.wtimer, self.flash = "firing", wdef.cycle_tics, wdef.flash_tics
            if wdef.ammo:
                self.ammo[wdef.ammo] -= wdef.ammo_per_shot
            game.player_attack(wdef, accurate)
        elif not cmd.fire:
            self.refire = 0
        self.pending = None if self.pending == self.weapon else self.pending

    @property
    def weapon_frame(self) -> str:
        """Frame of the held weapon sprite: "ready" or "fire"."""
        return "fire" if self.flash > 0 else "ready"
