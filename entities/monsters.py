"""Monsters: a state machine idle -> chase -> attack/pain -> dead. Parameters live in the monsters definitions."""
from __future__ import annotations

import math

from config import MELEE_RANGE, STEP_HEIGHT
from entities.base import Entity
from gameplay import combat

_D = 0.70710678
DIRS = [(1, 0), (_D, _D), (0, 1), (-_D, _D), (-1, 0), (-_D, -_D), (0, -1), (_D, -_D)]   # 8 directions, as in Doom
MONSTER_SPREAD_DEG = 22.5          # monster hitscan spread (large in Doom)


class Monster(Entity):
    kind = "monster"

    def __init__(self, mdef, x: float, y: float, z: float = 0.0, angle: float = 0.0):
        super().__init__(x, y, z, mdef.radius, mdef.height, angle)
        self.mdef = mdef
        self.kind = mdef.id
        self.solid = self.shootable = True
        self.health = mdef.health
        self.state = "idle"             # idle | chase | attack | pain | dead
        self.timer = 0
        self.step_timer = 0
        self.movecount = 0
        self.movedir: int | None = None
        self.attack_kind = ""
        self.attack_done = False
        self.frame_toggle = 0
        self._refresh_sprite()

    @property
    def alive(self) -> bool:
        return self.state != "dead"

    # --- graphics -----------------------------------------------------------
    def _refresh_sprite(self) -> None:
        frame = {"idle": "A", "chase": "BC"[self.frame_toggle], "attack": "D",
                 "pain": "E", "dead": "F"}[self.state]
        self.sprite = f"{self.mdef.sprite}_{frame}"

    # --- logic ------------------------------------------------------------
    def tick(self, game) -> None:
        game.update_z(self)
        if self.state == "dead":
            return
        player = game.player
        if self.state == "idle":
            self._look(game, player)
        elif not player.alive:
            self.state = "idle"
        elif self.state == "chase":
            self._chase(game, player)
        elif self.state == "attack":
            self._attack_tick(game, player)
        elif self.state == "pain":
            self.timer -= 1
            if self.timer <= 0:
                self.state, self.step_timer = "chase", 0
        self._refresh_sprite()

    def wake(self, game) -> None:
        if self.state == "idle":
            self.state, self.step_timer, self.movecount = "chase", 0, 0
            if self.mdef.sight_sound:
                game.play_sound(self.mdef.sight_sound, self.x, self.y)

    def _look(self, game, player) -> None:
        if not player.alive or not game.has_los(self, player):
            return
        dist = self.distance_to(player)
        a = math.degrees(math.atan2(player.y - self.y, player.x - self.x))
        in_front = abs((a - self.angle + 180) % 360 - 180) <= 90
        if in_front or dist <= MELEE_RANGE:
            self.wake(game)

    def _face(self, target) -> None:
        self.angle = math.degrees(math.atan2(target.y - self.y, target.x - self.x))

    def _chase(self, game, player) -> None:
        if self.step_timer > 0:
            self.step_timer -= 1
            return
        self.step_timer = self.mdef.move_interval - 1
        self.frame_toggle ^= 1
        dist = self.distance_to(player)
        m = self.mdef
        if m.melee_damage and dist < MELEE_RANGE - 20 + player.radius:
            return self._start_attack("melee", player)
        if m.missile and self.movecount <= 0 and self._missile_range_ok(game, player, dist):
            return self._start_attack("missile", player)
        self.movecount -= 1
        if self.movecount < 0 or self.movedir is None or not self._try_dir(game, self.movedir):
            self._new_chase_dir(game, player)

    def _missile_range_ok(self, game, player, dist: float) -> bool:
        """Like P_CheckMissileRange: the closer the target, the more often it fires."""
        if not game.has_los(self, player) or dist > 14 * 64:
            return False
        d = dist - 64
        if not self.mdef.melee_damage:
            d -= 128
        return game.rng.randrange(256) >= max(0.0, min(d, 200.0))

    def _try_dir(self, game, d: int) -> bool:
        dx, dy = DIRS[d]
        s = self.mdef.speed
        self.angle = d * 45.0
        return game.try_step(self, dx * s, dy * s)

    def _new_chase_dir(self, game, player) -> None:
        pref = round(math.degrees(math.atan2(player.y - self.y, player.x - self.x)) / 45.0) % 8
        side = game.rng.choice((1, -1))
        order = [pref, (pref + side) % 8, (pref - side) % 8, (pref + 2 * side) % 8, (pref - 2 * side) % 8]
        rest = [d for d in range(8) if d not in order]
        game.rng.shuffle(rest)
        order += rest
        back = None if self.movedir is None else (self.movedir + 4) % 8
        if back in order:
            order.remove(back)
            order.append(back)           # turning back is the last resort
        for d in order:
            if self._try_dir(game, d):
                self.movedir = d
                self.movecount = game.rng.randint(0, 15)
                return
        self.movedir, self.movecount = None, 0

    def _start_attack(self, kind: str, player) -> None:
        self.state, self.attack_kind, self.attack_done = "attack", kind, False
        self.timer = self.mdef.windup_tics
        self._face(player)

    def _attack_tick(self, game, player) -> None:
        self.timer -= 1
        if self.timer > 0:
            if not self.attack_done:
                self._face(player)
            return
        m = self.mdef
        if not self.attack_done:
            self.attack_done = True
            self._face(player)
            self._do_attack(game, player)
            self.timer = m.recovery_tics
            return
        self.state, self.step_timer = "chase", 0
        self.movecount = game.rng.randint(0, 15)

    def _do_attack(self, game, player) -> None:
        m = self.mdef
        if m.attack_sound:
            game.play_sound(m.attack_sound, self.x, self.y)
        if self.attack_kind == "melee":
            if self.distance_to(player) < MELEE_RANGE - 20 + player.radius:
                player.take_damage(game, m.melee_damage.roll(game.rng), self)
        elif m.missile == "hitscan":
            spread = MONSTER_SPREAD_DEG * (game.rng.random() - game.rng.random())
            combat.hitscan_attack(game, self, self.angle + spread, combat.slope_to(self, player),
                                  m.missile_damage, 2048.0)
        elif m.missile == "projectile":
            combat.spawn_projectile(game, self, game.defs.projectiles[m.missile_projectile],
                                    self.angle, combat.slope_to(self, player))

    # --- damage --------------------------------------------------------------
    def take_damage(self, game, amount: int, source) -> None:
        if self.state == "dead":
            return
        self.health -= amount
        if self.health <= 0:
            return self._die(game)
        if self.state == "idle":
            self.wake(game)
        if game.rng.randrange(256) < self.mdef.pain_chance:
            self.state, self.timer = "pain", self.mdef.pain_tics
            if self.mdef.pain_sound:
                game.play_sound(self.mdef.pain_sound, self.x, self.y)
        self._refresh_sprite()

    def _die(self, game) -> None:
        self.state, self.solid, self.shootable = "dead", False, False
        if self.mdef.death_sound:
            game.play_sound(self.mdef.death_sound, self.x, self.y)
        if self.mdef.drop:
            game.spawn_pickup(self.mdef.drop, self.x, self.y)
        game.kills += 1
        game.bus.emit("monster_killed", game=game, monster=self)
        self._refresh_sprite()
