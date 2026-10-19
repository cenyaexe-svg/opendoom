"""Line builder from sector polygons (a convenient format for map authors).

The author describes only sectors as polygons. The builder:
  * orients polygons clockwise (interior to the right of the line, as in Doom);
  * inserts vertices at T-junctions;
  * turns shared edges into two-sided lines and the rest into one-sided lines;
  * assigns default side textures and applies `line_props`.

Default textures: a one-sided line uses its own sector's wall; a side of a two-sided line
sees the *neighbouring* sector's wall (a door looks like "door" because the door sector has wall="door").
"""
from __future__ import annotations

from world.geometry import Point, signed_area

Pt = tuple[float, float]


def _on_segment(p: Pt, a: Pt, b: Pt) -> bool:
    cr = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
    if abs(cr) > 1e-7:
        return False
    dot = (p[0] - a[0]) * (b[0] - a[0]) + (p[1] - a[1]) * (b[1] - a[1])
    return 1e-7 < dot < (b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2 - 1e-7


def _split_t_junctions(polys: dict[int, list[Pt]]) -> dict[int, list[Pt]]:
    all_pts = {p for poly in polys.values() for p in poly}
    out: dict[int, list[Pt]] = {}
    for sid, poly in polys.items():
        new: list[Pt] = []
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            new.append(a)
            between = [p for p in all_pts if _on_segment(p, a, b)]
            between.sort(key=lambda p: (p[0] - a[0]) ** 2 + (p[1] - a[1]) ** 2)
            new.extend(between)
        out[sid] = new
    return out


def build_from_polygons(spec: dict) -> dict:
    """Returns a copy of spec with explicit vertices and linedefs lists."""
    sectors = spec["sectors"]
    polys: dict[int, list[Pt]] = {}
    for i, s in enumerate(sectors):
        poly = [(float(x), float(y)) for x, y in s["polygon"]]
        if signed_area(poly) > 0:      # counter-clockwise -> reverse
            poly.reverse()
        polys[i] = poly
    polys = _split_t_junctions(polys)

    vindex: dict[Pt, int] = {}
    vertices: list[Pt] = []

    def vid(p: Pt) -> int:
        if p not in vindex:
            vindex[p] = len(vertices)
            vertices.append(p)
        return vindex[p]

    edges: dict[tuple[int, int], list[tuple[int, int, int]]] = {}
    for sid, poly in polys.items():
        for i, a in enumerate(poly):
            b = poly[(i + 1) % len(poly)]
            ia, ib = vid(a), vid(b)
            edges.setdefault((min(ia, ib), max(ia, ib)), []).append((sid, ia, ib))

    def default_side(sec_id: int, other_id: int | None) -> dict:
        src = sectors[other_id if other_id is not None else sec_id].get("wall", "tech")
        return {"upper": src, "lower": src, "middle": src}

    linedefs: list[dict] = []
    for key in sorted(edges):
        users = edges[key]
        if len(users) > 2:
            raise ValueError(f"Edge {vertices[key[0]]}-{vertices[key[1]]} is used by more than two sectors")
        sid, ia, ib = users[0]
        if len(users) == 1:
            linedefs.append({"v1": ia, "v2": ib, "front": sid, "back": None,
                             "front_tex": default_side(sid, None)})
        else:
            sid2, ja, jb = users[1]
            if (ia, ib) == (ja, jb):
                raise ValueError(f"Sectors {sid} and {sid2} overlap at edge {vertices[ia]}-{vertices[ib]}")
            linedefs.append({"v1": ia, "v2": ib, "front": sid, "back": sid2,
                             "front_tex": default_side(sid, sid2), "back_tex": default_side(sid2, sid)})

    for prop in spec.get("line_props", []):
        a, b = tuple(map(float, prop["from"])), tuple(map(float, prop["to"]))
        if a not in vindex or b not in vindex:
            raise ValueError(f"line_props: no vertex for {prop['from']} -> {prop['to']}")
        want = {vindex[a], vindex[b]}
        match = [ln for ln in linedefs if {ln["v1"], ln["v2"]} == want]
        if not match:
            raise ValueError(f"line_props: no line {prop['from']} -> {prop['to']} (it may have been split by a T-junction)")
        ln = match[0]
        if "special" in prop:
            ln["special"] = prop["special"]
        for sec_key, tex in prop.get("textures", {}).items():     # texture of the side belonging to the sector
            sec_id = int(sec_key)
            side = "front_tex" if ln["front"] == sec_id else "back_tex" if ln["back"] == sec_id else None
            if side is None:
                raise ValueError(f"line_props: the line does not belong to sector {sec_id}")
            ln[side] = {"upper": tex, "lower": tex, "middle": tex}

    result = {k: v for k, v in spec.items() if k != "line_props"}
    result["sectors"] = [{k: v for k, v in s.items() if k != "polygon"} for s in sectors]
    result["vertices"] = [list(v) for v in vertices]
    result["linedefs"] = linedefs
    return result
