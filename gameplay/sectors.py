"""Moving sectors: doors (ceiling) and lifts (floor). Speeds and pauses are as in Doom."""
from __future__ import annotations

DOOR_SPEED = 2.0       # units per tic
DOOR_WAIT = 150        # tics spent open
LIFT_SPEED = 4.0
LIFT_WAIT = 105


class Door:
    def __init__(self, sector, target: float):
        self.sector, self.target = sector, target
        self.state, self.timer = "opening", 0

    def tick(self, game) -> bool:
        s = self.sector
        if self.state == "opening":
            s.ceiling = min(self.target, s.ceiling + DOOR_SPEED)
            if s.ceiling >= self.target:
                self.state, self.timer = "waiting", DOOR_WAIT
        elif self.state == "waiting":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "closing"
                game.sectors.sound(game, s, "door_close")
        elif self.state == "closing":
            new = max(s.floor, s.ceiling - DOOR_SPEED)
            if any(e.z + e.height > new for e in game.entities_in_sector(s)):
                self.state = "opening"                      # the door does not crush: it opens again
                game.sectors.sound(game, s, "door_open")
            else:
                s.ceiling = new
                if new <= s.floor:
                    return True
        return False


class Lift:
    def __init__(self, sector, low: float):
        self.sector, self.low, self.rest = sector, low, sector.floor
        self.state, self.timer = "lowering", 0

    def tick(self, game) -> bool:
        s = self.sector
        if self.state == "lowering":
            s.floor = max(self.low, s.floor - LIFT_SPEED)
            if s.floor <= self.low:
                self.state, self.timer = "waiting", LIFT_WAIT
        elif self.state == "waiting":
            self.timer -= 1
            if self.timer <= 0:
                self.state = "raising"
                game.sectors.sound(game, s, "lift_move")
        elif self.state == "raising":
            s.floor = min(self.rest, s.floor + LIFT_SPEED)
            if s.floor >= self.rest:
                return True
        return False


class SectorManager:
    def __init__(self) -> None:
        self.movers: dict[int, Door | Lift] = {}

    def sound(self, game, sector, name: str) -> None:
        pts = sector.outline[0] if sector.outline else [(0, 0)]
        game.play_sound(name, sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    def activate_door(self, game, sector) -> bool:
        m = self.movers.get(sector.id)
        if m is not None:
            if isinstance(m, Door) and m.state in ("waiting", "closing"):
                m.state = "closing" if m.state == "waiting" else "opening"
                self.sound(game, sector, "door_close" if m.state == "closing" else "door_open")
                return True
            return False
        neighbors = game.level.neighbors(sector)
        if not neighbors:
            return False
        target = min(n.ceiling for n in neighbors) - 4
        if target <= sector.ceiling:
            return False
        self.movers[sector.id] = Door(sector, target)
        self.sound(game, sector, "door_open")
        return True

    def activate_lift(self, game, sector) -> bool:
        if sector.id in self.movers:
            return False
        low = min([n.floor for n in game.level.neighbors(sector)] + [sector.floor])
        if low >= sector.floor:
            return False
        self.movers[sector.id] = Lift(sector, low)
        self.sound(game, sector, "lift_move")
        return True

    def tick(self, game) -> None:
        for sid in list(self.movers):
            if self.movers[sid].tick(game):
                del self.movers[sid]
