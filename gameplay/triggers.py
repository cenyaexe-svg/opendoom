"""Special lines: doors, lifts, exit. Triggered by use or by crossing (walk)."""
from __future__ import annotations

import math

from config import USE_RANGE
from world.collision import opening
from world.geometry import ray_segment

KEY_RU = {"red": "red", "blue": "blue", "yellow": "yellow"}


def _opposite_sector(game, line, x: float, y: float):
    """Sector on the other side of the line from the point (x, y). A line can be used from both sides."""
    cross = (line.x2 - line.x1) * (y - line.y1) - (line.y2 - line.y1) * (x - line.x1)
    other = line.back if cross < 0 else line.front          # right of the line is front
    return None if other is None else game.level.sectors[other]


def activate_line(game, line, activator, x: float, y: float) -> bool:
    sp = line.special
    if sp is None:
        return False
    is_player = activator is game.player
    if sp["key"] and (not is_player or sp["key"] not in game.player.keys):
        if is_player:
            game.message(f"You need a {KEY_RU[sp['key']]} keycard to open this door.")
            game.play_sound("noway", None, None)
        return False
    done = False
    if sp["action"] == "exit":
        if is_player:
            game.exit_level()
            done = True
    elif sp["action"] == "door":
        if sp["tag"]:
            targets = game.level.sectors_with_tag(sp["tag"])
        else:
            opp = _opposite_sector(game, line, x, y)
            targets = [opp] if opp is not None else []
        done = any([game.sectors.activate_door(game, s) for s in targets])
    elif sp["action"] == "lift":
        done = any([game.sectors.activate_lift(game, s) for s in game.level.sectors_with_tag(sp["tag"])])
    if done and not sp["repeat"]:
        line.special = None
    return done


def use_line(game, player) -> None:
    """A ray of length USE_RANGE: the first line with a use trigger fires; a solid wall stops the ray."""
    dx, dy = math.cos(math.radians(player.angle)), math.sin(math.radians(player.angle))
    hits = []
    for ln in game.level.linedefs:
        t = ray_segment(player.x, player.y, dx, dy, ln.x1, ln.y1, ln.x2, ln.y2)
        if t is not None and t <= USE_RANGE:
            hits.append((t, ln))
    for _, ln in sorted(hits, key=lambda h: h[0]):
        if ln.special and ln.special["trigger"] == "use":
            activate_line(game, ln, player, player.x, player.y)
            return
        if ln.back is None:
            game.play_sound("noway", None, None)
            return
        bottom, top = opening(game.level, ln)
        if top - bottom <= 0:
            return
