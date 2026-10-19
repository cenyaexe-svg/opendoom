"""Level geometry generation (no Panda3D): walls, floors and ceilings as vertex lists per texture.

Vertex: (x, y, z, u, v, brightness 0..1). Result: dict[texture] -> (vertices, triangle indices).
Sector lighting is encoded in vertex brightness; Doom-style "fake contrast": horizontal walls are darker, vertical ones lighter.
"""
from __future__ import annotations

from world.geometry import triangulate
from world.map_data import Level, Linedef

TEX = 64.0
Mesh = dict[str, tuple[list[tuple], list[int]]]


def _add_quad(mesh: Mesh, tex: str, pts: list[tuple], ) -> None:
    verts, idx = mesh.setdefault(tex, ([], []))
    base = len(verts)
    verts.extend(pts)
    idx.extend((base, base + 1, base + 2, base, base + 2, base + 3))


def _light(sector, line: Linedef) -> float:
    lv = sector.light
    if line.y1 == line.y2:
        lv -= 16
    elif line.x1 == line.x2:
        lv += 16
    return max(0.0, min(1.0, lv / 255.0))


def _wall(mesh, tex, line, x1, y1, x2, y2, z0, z1, light) -> None:
    if z1 - z0 <= 0.01:
        return
    u0, u1 = 0.0, line.length / TEX
    _add_quad(mesh, tex, [(x1, y1, z0, u0, z0 / TEX, light), (x2, y2, z0, u1, z0 / TEX, light),
                          (x2, y2, z1, u1, z1 / TEX, light), (x1, y1, z1, u0, z1 / TEX, light)])


def line_mesh(level: Level, line: Linedef) -> Mesh:
    """Visible wall parts of a line on both sides (uses the current sector heights)."""
    mesh: Mesh = {}
    f = level.sectors[line.front]
    if line.back is None:
        _wall(mesh, line.front_tex.middle, line, line.x1, line.y1, line.x2, line.y2, f.floor, f.ceiling, _light(f, line))
        return mesh
    b = level.sectors[line.back]
    # The front side faces sector f (right of the line): it sees the lower/upper walls on its own side.
    for sec, other, tex, (ax, ay, bx, by) in (
            (f, b, line.front_tex, (line.x1, line.y1, line.x2, line.y2)),
            (b, f, line.back_tex, (line.x2, line.y2, line.x1, line.y1))):
        light = _light(sec, line)
        if other.floor > sec.floor:
            _wall(mesh, tex.lower, line, ax, ay, bx, by, sec.floor, other.floor, light)
        if other.ceiling < sec.ceiling:
            _wall(mesh, tex.upper, line, ax, ay, bx, by, other.ceiling, sec.ceiling, light)
    return mesh


def sector_mesh(sector) -> Mesh:
    """Floor and ceiling of a sector (both from the outline, triangulated by ear clipping)."""
    mesh: Mesh = {}
    light = max(0.0, min(1.0, sector.light / 255.0))
    for loop in sector.outline:
        for a, b, c in triangulate(loop):                       # a,b,c are counter-clockwise (top view)
            for tex, z, order in ((sector.floor_tex, sector.floor, (a, b, c)),
                                  (sector.ceil_tex, sector.ceiling, (a, c, b))):
                verts, idx = mesh.setdefault(tex, ([], []))
                base = len(verts)
                verts.extend((p[0], p[1], z, p[0] / TEX, p[1] / TEX, light) for p in order)
                idx.extend((base, base + 1, base + 2))
    return mesh
