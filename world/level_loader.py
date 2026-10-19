"""Level loading from JSON (explicit vertices/linedefs format or polygon format)."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from world.builder import build_from_polygons
from world.geometry import Point, signed_area
from world.map_data import Level, Linedef, Sector, SideTextures, Thing

log = logging.getLogger("opendoom")

SPECIAL_ACTIONS = {"door", "lift", "exit"}
SPECIAL_TRIGGERS = {"use", "walk"}
KEY_NAMES = {"red", "blue", "yellow"}


class LevelError(ValueError):
    pass


def load_level(source: dict | str | Path) -> Level:
    spec = source if isinstance(source, dict) else json.loads(Path(source).read_text(encoding="utf-8"))
    if any("polygon" in s for s in spec.get("sectors", [])):
        spec = build_from_polygons(spec)
    return _make_level(spec)


def _side(d: dict | None) -> SideTextures | None:
    return None if d is None else SideTextures(d["upper"], d["lower"], d["middle"])


def _check_special(sp: dict, where: str) -> dict:
    action, trigger = sp.get("action"), sp.get("trigger", "use")
    if action not in SPECIAL_ACTIONS:
        raise LevelError(f"{where}: unknown action {action!r}")
    if trigger not in SPECIAL_TRIGGERS:
        raise LevelError(f"{where}: unknown trigger {trigger!r}")
    if sp.get("key") is not None and sp["key"] not in KEY_NAMES:
        raise LevelError(f"{where}: unknown key {sp['key']!r}")
    if action == "lift" and not sp.get("tag"):
        raise LevelError(f"{where}: lift requires a tag")
    return {"action": action, "trigger": trigger, "key": sp.get("key"), "tag": sp.get("tag", 0),
            "repeat": sp.get("repeat", True)}


def _make_level(spec: dict) -> Level:
    try:
        vertices = [(float(x), float(y)) for x, y in spec["vertices"]]
        sectors = [Sector(id=i, floor=float(s["floor"]), ceiling=float(s["ceiling"]),
                          light=int(s.get("light", 160)), floor_tex=s.get("floor_tex", "stone"),
                          ceil_tex=s.get("ceil_tex", "panel"), wall_tex=s.get("wall", "tech"),
                          tag=int(s.get("tag", 0)), damage=int(s.get("damage", 0)),
                          secret=bool(s.get("secret", False)))
                   for i, s in enumerate(spec["sectors"])]
        lines: list[Linedef] = []
        for i, d in enumerate(spec["linedefs"]):
            back = d.get("back")
            for idx in (d["v1"], d["v2"]):
                if not 0 <= idx < len(vertices):
                    raise LevelError(f"linedef {i}: invalid vertex index {idx}")
            for sid in (d["front"], back):
                if sid is not None and not 0 <= sid < len(sectors):
                    raise LevelError(f"linedef {i}: invalid sector {sid}")
            special = _check_special(d["special"], f"linedef {i}") if d.get("special") else None
            lines.append(Linedef(i, d["v1"], d["v2"], d["front"], back, _side(d["front_tex"]),
                                 _side(d.get("back_tex")), special))
        things = [Thing(t["type"], float(t["x"]), float(t["y"]), float(t.get("angle", 0)))
                  for t in spec.get("things", [])]
    except KeyError as e:
        raise LevelError(f"The level description is missing field {e}") from e
    for s in sectors:
        if s.ceiling < s.floor:
            raise LevelError(f"sector {s.id}: ceiling below floor")
    level = Level(spec.get("name", "unnamed"), vertices, sectors, lines, things, spec.get("next"))
    for sec in sectors:
        sec.outline = _sector_outline(level, sec)
    if not any(t.type == "player_start" for t in things):
        raise LevelError("The level has no player_start thing")
    return level


def _sector_outline(level: Level, sec: Sector) -> list[list[Point]]:
    """Sector outlines (interior on the right). Holes are ignored with a warning."""
    edges: dict[int, list[int]] = {}
    ends: dict[tuple[int, int], int] = {}
    for ln in level.linedefs:
        if ln.front == sec.id:
            edges.setdefault(ln.v1, []).append(ln.v2)
        if ln.back == sec.id:
            edges.setdefault(ln.v2, []).append(ln.v1)
    loops: list[list[Point]] = []
    while edges:
        start = next(iter(edges))
        loop, cur = [start], start
        while True:
            nxt = edges[cur].pop(0)
            if not edges[cur]:
                del edges[cur]
            if nxt == start:
                break
            loop.append(nxt)
            cur = nxt
            if cur not in edges:
                raise LevelError(f"sector {sec.id}: outline is not closed")
        loops.append([level.vertices[i] for i in loop])
    outer = [lp for lp in loops if signed_area(lp) < 0]
    if len(outer) != len(loops):
        log.warning("sector %d: holes in a sector are not supported by the renderer (floor/ceiling will be incomplete)", sec.id)
    return outer
