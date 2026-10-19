"""Collisions and ray tracing against level lines."""
from __future__ import annotations

import math

from world.geometry import point_segment_dist, ray_segment
from world.map_data import Level, Linedef


def opening(level: Level, line: Linedef) -> tuple[float, float]:
    """(bottom, top) of a two-sided line's opening."""
    f, b = level.sectors[line.front], level.sectors[line.back]
    return max(f.floor, b.floor), min(f.ceiling, b.ceiling)


def line_blocks(level: Level, line: Linedef, z: float, height: float, step: float,
                max_drop: float | None = None) -> bool:
    """Whether the line blocks a creature (Doom rules: opening, step, drop-off)."""
    if line.back is None:
        return True
    f, b = level.sectors[line.front], level.sectors[line.back]
    bottom, top = max(f.floor, b.floor), min(f.ceiling, b.ceiling)
    if top - bottom < height or top - z < height or bottom - z > step:
        return True
    return max_drop is not None and z - min(f.floor, b.floor) > max_drop


def blocking_line(level: Level, x: float, y: float, radius: float, z: float, height: float,
                  step: float, max_drop: float | None = None) -> Linedef | None:
    """Nearest blocking line within the circle of the given radius, or None."""
    best, best_d = None, radius
    for ln in level.linedefs:
        d = point_segment_dist(x, y, ln.x1, ln.y1, ln.x2, ln.y2)
        if d < best_d and line_blocks(level, ln, z, height, step, max_drop):
            best, best_d = ln, d
    return best


def position_valid(level: Level, x: float, y: float, radius: float, z: float, height: float,
                   step: float, max_drop: float | None = None) -> bool:
    return level.sector_at(x, y) is not None and \
        blocking_line(level, x, y, radius, z, height, step, max_drop) is None


def slide_move(level: Level, x: float, y: float, dx: float, dy: float, radius: float, z: float,
               height: float, step: float) -> tuple[float, float]:
    """Movement with sliding along walls. Returns the new position."""
    nx, ny = x + dx, y + dy
    blocker = blocking_line(level, nx, ny, radius, z, height, step)
    if blocker is None:
        return (nx, ny) if level.sector_at(nx, ny) is not None else (x, y)
    ux, uy = blocker.x2 - blocker.x1, blocker.y2 - blocker.y1
    norm = math.hypot(ux, uy) or 1.0
    ux, uy = ux / norm, uy / norm
    d = dx * ux + dy * uy
    sx, sy = x + ux * d, y + uy * d
    if blocking_line(level, sx, sy, radius, z, height, step) is None and level.sector_at(sx, sy) is not None:
        return sx, sy
    return x, y


def trace_ray(level: Level, ox: float, oy: float, oz: float, dx: float, dy: float,
              slope: float, max_dist: float) -> tuple[float, Linedef | None]:
    """First obstacle on the ray: (distance, line). The line is None if the path is clear.

    A two-sided line blocks the ray if the ray height at the crossing is outside the opening.
    """
    best, best_line = max_dist, None
    for ln in level.linedefs:
        t = ray_segment(ox, oy, dx, dy, ln.x1, ln.y1, ln.x2, ln.y2)
        if t is None or t >= best:
            continue
        if ln.back is not None:
            bottom, top = opening(level, ln)
            z = oz + slope * t
            if bottom <= z <= top:
                continue
        best, best_line = t, ln
    return best, best_line


def has_line_of_sight(level: Level, ax: float, ay: float, az: float, bx: float, by: float, bz: float) -> bool:
    dist = math.hypot(bx - ax, by - ay)
    if dist < 1e-6:
        return True
    hit, _ = trace_ray(level, ax, ay, az, (bx - ax) / dist, (by - ay) / dist, (bz - az) / dist, dist)
    return hit >= dist - 0.01
