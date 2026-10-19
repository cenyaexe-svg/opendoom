"""Pure 2D geometry with no dependency on the game."""
from __future__ import annotations

import math

Point = tuple[float, float]
EPS = 1e-9


def signed_area(poly: list[Point]) -> float:
    """Positive for counter-clockwise winding."""
    return 0.5 * sum(poly[i][0] * poly[(i + 1) % len(poly)][1] - poly[(i + 1) % len(poly)][0] * poly[i][1]
                     for i in range(len(poly)))


def cross(o: Point, a: Point, b: Point) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def point_segment_dist(px: float, py: float, x1: float, y1: float, x2: float, y2: float) -> float:
    dx, dy = x2 - x1, y2 - y1
    len2 = dx * dx + dy * dy
    t = 0.0 if len2 == 0 else max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / len2))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


def segments_intersect(a: Point, b: Point, c: Point, d: Point) -> bool:
    d1, d2 = cross(c, d, a), cross(c, d, b)
    d3, d4 = cross(a, b, c), cross(a, b, d)
    return ((d1 > 0) != (d2 > 0)) and ((d3 > 0) != (d4 > 0))


def ray_segment(ox: float, oy: float, dx: float, dy: float,
                x1: float, y1: float, x2: float, y2: float) -> float | None:
    """Distance along the ray (dx, dy is a unit vector) to the segment, or None."""
    ex, ey = x2 - x1, y2 - y1
    denom = dx * ey - dy * ex
    if abs(denom) < EPS:
        return None
    ax, ay = x1 - ox, y1 - oy
    t = (ax * ey - ay * ex) / denom
    u = (ax * dy - ay * dx) / denom
    if t < 1e-6 or u < 0.0 or u > 1.0:
        return None
    return t


def ray_circle(ox: float, oy: float, dx: float, dy: float,
               cx: float, cy: float, r: float) -> float | None:
    """Distance along the ray to the circle entry point (0 if the origin is inside)."""
    fx, fy = cx - ox, cy - oy
    b = fx * dx + fy * dy
    disc = r * r - (fx * fx + fy * fy - b * b)
    if disc < 0:
        return None
    root = math.sqrt(disc)
    if b + root < 0:
        return None
    return max(0.0, b - root)


def strip_collinear(poly: list[Point]) -> list[Point]:
    out = list(poly)
    changed = True
    while changed and len(out) > 3:
        changed = False
        for i in range(len(out)):
            if abs(cross(out[i - 1], out[i], out[(i + 1) % len(out)])) < 1e-7:
                out.pop(i)
                changed = True
                break
    return out


def triangulate(poly: list[Point]) -> list[tuple[Point, Point, Point]]:
    """Ear clipping for a simple polygon (no holes)."""
    pts = strip_collinear(list(poly))
    if signed_area(pts) < 0:
        pts.reverse()
    idx = list(range(len(pts)))
    tris: list[tuple[Point, Point, Point]] = []

    def inside(p: Point, a: Point, b: Point, c: Point) -> bool:
        return cross(a, b, p) >= -1e-7 and cross(b, c, p) >= -1e-7 and cross(c, a, p) >= -1e-7

    while len(idx) > 3:
        for k in range(len(idx)):
            i0, i1, i2 = idx[k - 1], idx[k], idx[(k + 1) % len(idx)]
            a, b, c = pts[i0], pts[i1], pts[i2]
            if cross(a, b, c) <= 1e-7:
                continue
            if any(inside(pts[j], a, b, c) for j in idx if j not in (i0, i1, i2)):
                continue
            tris.append((a, b, c))
            idx.pop(k)
            break
        else:
            raise ValueError("Cannot triangulate sector (self-intersection or a hole?)")
    tris.append((pts[idx[0]], pts[idx[1]], pts[idx[2]]))
    return tris
