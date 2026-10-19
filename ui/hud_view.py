"""HUD display in Panda3D: status bar, held weapon, damage/pickup flashes, messages."""
from __future__ import annotations

import math

from direct.gui.OnscreenText import OnscreenText
from panda3d.core import CardMaker, NodePath, TextNode, Texture, SamplerState, TransparencyAttrib

from config import WEAPON_BOTTOM
from ui.hud import StatusBar

MESSAGE_TICS = 105
BAR_TOP = -0.68               # the bar takes 32/200 of the screen height (as in Doom)
WEAPON_SCALE = 2              # 320x200 screen pixels per weapon sprite pixel


class HudView:
    def __init__(self, base, textures):
        self.base, self.textures = base, textures
        r2d = base.render2d
        self.bar_canvas = StatusBar()
        self.bar_tex = Texture("statusbar")
        self.bar_tex.setup2dTexture(StatusBar.W, StatusBar.H, Texture.T_unsigned_byte, Texture.F_rgba)
        for f in (self.bar_tex.setMagfilter, self.bar_tex.setMinfilter):
            f(SamplerState.FT_nearest)
        self.weapon = self._card(r2d, "weapon", (-0.5, 0.5, 0, 1), 10)
        self.bar = self._card(r2d, "bar", (-1, 1, -1, BAR_TOP), 20)
        self.bar.setTexture(self.bar_tex, 1)
        self.flash = self._card(r2d, "flash", (-1, 1, BAR_TOP, 1), 5)
        self.text = OnscreenText("", pos=(-0.97, 0.9), scale=0.06, fg=(1, 0.9, 0.4, 1), shadow=(0, 0, 0, 1),
                                 align=TextNode.ALeft, mayChange=True, parent=r2d)
        self.center = OnscreenText("", pos=(0, 0.1), scale=0.09, fg=(1, 0.3, 0.2, 1), shadow=(0, 0, 0, 1),
                                   align=TextNode.ACenter, mayChange=True, parent=r2d)
        self._msg_until = -1
        self._weapon_key = None

    @staticmethod
    def _card(parent, name, frame, sort) -> NodePath:
        cm = CardMaker(name)
        cm.setFrame(*frame)
        n = parent.attachNewNode(cm.generate())
        n.setBin("fixed", sort)
        n.setDepthTest(False)
        n.setDepthWrite(False)
        n.setTransparency(TransparencyAttrib.M_alpha)
        return n

    def show_message(self, text: str, tic: int) -> None:
        self.text.setText(text)
        self._msg_until = tic + MESSAGE_TICS

    def set_center(self, text: str) -> None:
        self.center.setText(text)

    def update(self, game) -> None:
        p = game.player
        canvas, changed = self.bar_canvas.render(game)
        if changed:
            self.bar_tex.setRamImage(canvas.to_panda_ram())
        if game.tic > self._msg_until:
            self.text.setText("")
        self._update_weapon(game)
        if p.damage_count > 0:
            self.flash.setColor(0.8, 0.05, 0.05, min(0.55, p.damage_count / 40.0))
        elif p.bonus_count > 0:
            self.flash.setColor(0.9, 0.8, 0.2, 0.18)
        else:
            self.flash.setColor(0, 0, 0, 0)

    def _update_weapon(self, game) -> None:
        p = game.player
        wdef = game.defs.weapons[p.weapon]
        key = (wdef.sprite, p.weapon_frame)
        if key != self._weapon_key:
            tex, w, h = self.textures.get("sprite", f"{wdef.sprite}:{p.weapon_frame}")
            self.weapon.setTexture(tex, 1)
            self._wh = (w * WEAPON_SCALE, h * WEAPON_SCALE)
            self._weapon_key = key
        t = wdef.tint or (1, 1, 1)
        self.weapon.setColorScale(*t, 1)
        phase = 2 * math.pi * game.tic / 64.0
        bx, by = p.bob * math.cos(phase), p.bob * abs(math.sin(phase))
        lowered = max(0.0, p.wy - 32.0)
        w_px, h_px = self._wh
        self.weapon.setScale(2 * w_px / 320.0, 1, 2 * h_px / 200.0)
        self.weapon.setPos(bx * 2 / 320.0, 0, BAR_TOP - 2 * (lowered + by) / 200.0)
        self.weapon.setColorScale(*t, 0.0 if p.wy >= WEAPON_BOTTOM else 1.0)
