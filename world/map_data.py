"""Doom-style level data structures: vertices, lines, sectors, things."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from world.geometry import Point, point_segment_dist


@dataclass
class Sector:
    id: int
    floor: float
    ceiling: float
    light: int = 160                       # 0..255
    floor_tex: str = "stone"
    ceil_tex: str = "panel"
    wall_tex: str = "tech"
    tag: int = 0
    damage: int = 0                        # damage every 32 tics (like Doom's nukage)
    secret: bool = False
    outline: list[list[Point]] = field(default_factory=list)   # filled in by the loader


@dataclass
class SideTextures:
    upper: str
    lower: str
    middle: str


@dataclass
class Linedef:
    id: int
    v1: int
    v2: int
    front: int
    back: int | None
    front_tex: SideTextures
    back_tex: SideTextures | None = None
    special: dict | None = None
    # coordinates and length are computed in Level
    x1: float = 0.0
    y1: float = 0.0
    x2: float = 0.0
    y2: float = 0.0
    length: float = 0.0


@dataclass
class Thing:
    type: str
    x: float
    y: float
    angle: float = 0.0


@dataclass
class Level:
    name: str
    vertices: list[Point]
    sectors: list[Sector]
    linedefs: list[Linedef]
    things: list[Thing]
    next_map: str | None = None

    def __post_init__(self) -> None:
        for line in self.linedefs:
            line.x1, line.y1 = self.vertices[line.v1]
            line.x2, line.y2 = self.vertices[line.v2]
            line.length = math.hypot(line.x2 - line.x1, line.y2 - line.y1)

    # --- queries ---------------------------------------------------------
    def sector_at(self, x: float, y: float) -> Sector | None:
        """Sector containing the point (parity of +X ray crossings with sector boundaries)."""
        parity = [0] * len(self.sectors)
        for ln in self.linedefs:
            if (ln.y1 > y) != (ln.y2 > y):
                xi = ln.x1 + (y - ln.y1) * (ln.x2 - ln.x1) / (ln.y2 - ln.y1)
                if xi > x:
                    parity[ln.front] ^= 1
                    if ln.back is not None and ln.back != ln.front:
                        parity[ln.back] ^= 1
        for i, p in enumerate(parity):
            if p:
                return self.sectors[i]
        return None

    def floor_ceiling_at(self, x: float, y: float, radius: float, step: float) -> tuple[float, float] | None:
        """Floor and ceiling under a circle of the given radius (like floorz/ceilingz in Doom)."""
        sec = self.sector_at(x, y)
        if sec is None:
            return None
        floor, ceil = sec.floor, sec.ceiling
        for ln in self.linedefs:
            if ln.back is None:
                continue
            if point_segment_dist(x, y, ln.x1, ln.y1, ln.x2, ln.y2) < radius:
                for s in (self.sectors[ln.front], self.sectors[ln.back]):
                    if s.floor - sec.floor <= step:
                        floor = max(floor, s.floor)
                    ceil = min(ceil, s.ceiling)
        return floor, ceil

    def sectors_with_tag(self, tag: int) -> list[Sector]:
        return [s for s in self.sectors if tag and s.tag == tag]

    def neighbors(self, sector: Sector) -> list[Sector]:
        found: dict[int, Sector] = {}
        for ln in self.linedefs:
            if ln.back is None:
                continue
            if ln.front == sector.id:
                found[ln.back] = self.sectors[ln.back]
            elif ln.back == sector.id:
                found[ln.front] = self.sectors[ln.front]
        return list(found.values())

    def lines_of_sector(self, sector: Sector) -> list[Linedef]:
        return [ln for ln in self.linedefs if sector.id in (ln.front, ln.back)]
