"""Level and sprite rendering with Panda3D. Reads Game state but never modifies it.

Geometry is built from rendering/meshgen.py; moving sectors (doors, lifts) are rebuilt when their heights change.
Textures use nearest filtering (pixel look); lighting is vertex brightness from sector light plus darkening fog.
"""
from __future__ import annotations

import logging

from panda3d.core import (CardMaker, Fog, Geom, GeomNode, GeomTriangles, GeomVertexData, GeomVertexFormat,
                          GeomVertexWriter, NodePath, RenderState, SamplerState, Texture, TextureAttrib,
                          TransparencyAttrib)

from rendering.canvas import Canvas
from rendering.meshgen import line_mesh, sector_mesh
from rendering.sprites import make_sprite
from rendering.textures import make_texture

log = logging.getLogger("opendoom")


class TextureLibrary:
    """Textures and sprites: PNG from resources (mods take priority) or procedural."""

    def __init__(self, loader, resources):
        self.loader, self.res = loader, resources
        self._tex: dict[tuple[str, str], tuple[Texture, int, int]] = {}

    def _from_canvas(self, name: str, c: Canvas) -> Texture:
        t = Texture(name)
        t.setup2dTexture(c.w, c.h, Texture.T_unsigned_byte, Texture.F_rgba)
        t.setRamImage(c.to_panda_ram())
        return t

    def get(self, kind: str, name: str) -> tuple[Texture, int, int]:
        key = (kind, name)
        if key not in self._tex:
            path = self.res.find("textures" if kind == "texture" else "sprites", name.replace(":", "_") + ".png")
            if path is not None:
                from panda3d.core import Filename
                t = self.loader.loadTexture(Filename.fromOsSpecific(str(path)))
                size = (t.getXSize(), t.getYSize())
            else:
                c = make_texture(name) if kind == "texture" else make_sprite(name)
                t, size = self._from_canvas(name, c), (c.w, c.h)
            t.setMagfilter(SamplerState.FT_nearest)
            t.setMinfilter(SamplerState.FT_nearest)
            self._tex[key] = (t, *size)
        return self._tex[key]


def _geom_node(name: str, mesh, textures: TextureLibrary) -> GeomNode:
    gnode = GeomNode(name)
    for tex_name, (verts, idx) in mesh.items():
        vdata = GeomVertexData(name, GeomVertexFormat.getV3c4t2(), Geom.UHStatic)
        vdata.setNumRows(len(verts))
        vw, cw, tw = (GeomVertexWriter(vdata, c) for c in ("vertex", "color", "texcoord"))
        for x, y, z, u, v, light in verts:
            vw.addData3(x, y, z)
            cw.addData4(light, light, light, 1.0)
            tw.addData2(u, v)
        prim = GeomTriangles(Geom.UHStatic)
        for i in range(0, len(idx), 3):
            prim.addVertices(idx[i], idx[i + 1], idx[i + 2])
        geom = Geom(vdata)
        geom.addPrimitive(prim)
        gnode.addGeom(geom, RenderState.make(TextureAttrib.make(textures.get("texture", tex_name)[0])))
    return gnode


class LevelRenderer:
    FOG_END = 1600.0

    def __init__(self, base, game, resources, textures: TextureLibrary):
        self.base, self.game, self.textures = base, game, textures
        self.root = base.render.attachNewNode("level")
        self.root.setTwoSided(True)                       # independent of vertex winding order
        fog = Fog("doom-fog")
        fog.setColor(0, 0, 0)
        fog.setLinearRange(0, self.FOG_END)
        self.root.setFog(fog)
        self._line_nodes: dict[int, NodePath] = {}
        self._sector_nodes: dict[int, NodePath] = {}
        self._heights: dict[int, tuple[float, float]] = {}
        self._sprites: dict[int, tuple[NodePath, str]] = {}
        for sec in game.level.sectors:
            self._build_sector(sec)
        for ln in game.level.linedefs:
            self._build_line(ln)

    # --- static/dynamic -------------------------------------------------
    def _build_sector(self, sec) -> None:
        old = self._sector_nodes.pop(sec.id, None)
        if old:
            old.removeNode()
        self._sector_nodes[sec.id] = self.root.attachNewNode(_geom_node(f"sector{sec.id}", sector_mesh(sec), self.textures))
        self._heights[sec.id] = (sec.floor, sec.ceiling)

    def _build_line(self, ln) -> None:
        old = self._line_nodes.pop(ln.id, None)
        if old:
            old.removeNode()
        self._line_nodes[ln.id] = self.root.attachNewNode(_geom_node(f"line{ln.id}", line_mesh(self.game.level, ln), self.textures))

    def _rebuild_changed(self) -> None:
        changed = {s.id for s in self.game.level.sectors if self._heights[s.id] != (s.floor, s.ceiling)}
        if not changed:
            return
        for sid in changed:
            self._build_sector(self.game.level.sectors[sid])
        for ln in self.game.level.linedefs:
            if ln.front in changed or ln.back in changed:
                self._build_line(ln)

    # --- sprites -------------------------------------------------------------
    def _sync_sprites(self) -> None:
        alive_ids = set()
        for e in self.game.entities:
            if e is self.game.player or e.removed or not e.sprite:
                continue
            key = id(e)
            alive_ids.add(key)
            tex, w, h = self.textures.get("sprite", e.sprite)
            node, cur = self._sprites.get(key, (None, None))
            if node is None:
                cm = CardMaker("sprite")
                cm.setFrame(-0.5, 0.5, 0, 1)
                node = self.root.attachNewNode(cm.generate())
                node.setBillboardAxis()
                node.setTwoSided(True)
                node.setTransparency(TransparencyAttrib.M_binary)
            if cur != e.sprite:
                node.setTexture(tex, 1)
                node.setScale(w, 1, h)
                self._sprites[key] = (node, e.sprite)
            lift = -h / 2 if e.kind == "projectile" else 0.0
            node.setPos(e.x, e.y, e.z + lift)
            sec = self.game.level.sector_at(e.x, e.y)
            light = 1.0 if e.fullbright or sec is None else max(0.15, sec.light / 255.0)
            tint = e.tint or (1, 1, 1)
            node.setColorScale(light * tint[0], light * tint[1], light * tint[2], 1)
            if e.fullbright:
                node.setFogOff()
        for key in [k for k in self._sprites if k not in alive_ids]:
            self._sprites.pop(key)[0].removeNode()

    # --- frame ----------------------------------------------------------------
    def update(self, alpha: float) -> None:
        self._rebuild_changed()
        self._sync_sprites()
        p = self.game.player
        lerp = lambda a, b: a + (b - a) * alpha
        self.base.camera.setPos(lerp(p.prev_x, p.x), lerp(p.prev_y, p.y), lerp(p.prev_z, p.z) + p.view_height)
        self.base.camera.setHpr(p.angle - 90.0, 0, 0)       # angle 0 = +X, Panda: heading 0 = +Y

    def destroy(self) -> None:
        self.root.removeNode()
