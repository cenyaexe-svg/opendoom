"""Classic 320x32 status bar: AMMO | HEALTH | ARMS | face | ARMOR | keys | ammo reserves.

Drawn in software into a Canvas (no Panda3D) and refreshed only when the data changes.
"""
from __future__ import annotations

from rendering.canvas import Canvas, rgb, shade

FONT_ROWS = {
    "0": "01110 10001 10011 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00010 00100 01000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "E": "11111 10000 10000 11110 10000 10000 11111",
    "H": "10001 10001 10001 11111 10001 10001 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "R": "11110 10001 10001 11110 10100 10010 10001", "S": "01111 10000 10000 01110 00001 00001 11110",
    "T": "11111 00100 00100 00100 00100 00100 00100", "U": "10001 10001 10001 10001 10001 10001 01110",
    "%": "11001 11010 00010 00100 01000 01011 10011", "/": "00001 00010 00010 00100 01000 01000 10000",
    "-": "00000 00000 00000 11111 00000 00000 00000",
}
RED, GREY, BAR = rgb(200, 30, 20), rgb(150, 150, 150), rgb(78, 78, 84)
KEY_COLORS = {"red": rgb(220, 40, 40), "blue": rgb(50, 80, 230), "yellow": rgb(240, 210, 40)}


def draw_text(c: Canvas, text: str, x: int, y: int, color, scale: int = 1) -> int:
    for ch in text.upper():
        rows = FONT_ROWS.get(ch)
        if rows:
            for ry, row in enumerate(rows.split()):
                for rx, bit in enumerate(row):
                    if bit == "1":
                        c.rect(x + rx * scale, y + ry * scale, scale, scale, color)
        x += 6 * scale
    return x


def draw_face(c: Canvas, x: int, y: int, health: int, hurt: bool, look: int = 0) -> None:
    """24x28 Doom-style face: the lower the health, the more blood; look: -1/0/1 is the gaze direction."""
    c.rect(x, y, 24, 28, rgb(60, 40, 30))
    if health <= 0:
        c.ellipse(x + 12, y + 15, 10, 12, rgb(140, 90, 70))
        c.rect(x + 6, y + 10, 4, 1, rgb(20, 10, 10)); c.rect(x + 14, y + 10, 4, 1, rgb(20, 10, 10))
        c.rect(x + 7, y + 7, 2, 4, rgb(150, 10, 10)); c.rect(x + 10, y + 20, 5, 2, rgb(150, 10, 10))
        return
    c.ellipse(x + 12, y + 15, 10, 12, rgb(215, 160, 125))
    c.rect(x + 2, y + 3, 20, 5, rgb(95, 65, 35))                       # hair
    c.rect(x + 6 + look, y + 11, 4, 3, rgb(240, 240, 240)); c.rect(x + 14 + look, y + 11, 4, 3, rgb(240, 240, 240))
    c.rect(x + 8 + look, y + 12, 2, 2, rgb(30, 30, 30)); c.rect(x + 16 + look, y + 12, 2, 2, rgb(30, 30, 30))
    c.rect(x + 5, y + 9, 6, 1, rgb(60, 40, 25)); c.rect(x + 13, y + 9, 6, 1, rgb(60, 40, 25))
    c.rect(x + 8, y + 21, 8, 2 if not hurt else 3, rgb(120, 40, 40))
    level = 0 if health > 80 else 1 if health > 60 else 2 if health > 40 else 3 if health > 20 else 4
    for i in range(level * 2):                                         # blood grows as health drops
        c.rect(x + 3 + (i * 5) % 17, y + 8 + (i * 7) % 15, 3, 2, rgb(150, 10, 10))
    if level >= 3:
        c.rect(x + 2, y + 14, 4, 8, rgb(140, 15, 15))


class StatusBar:
    W, H = 320, 32

    def __init__(self) -> None:
        self.canvas = Canvas(self.W, self.H)
        self._last = None

    def render(self, game) -> tuple[Canvas, bool]:
        """Returns (canvas, whether it changed). The face reacts to damage."""
        p, defs = game.player, game.defs
        wdef = defs.weapons[p.weapon]
        look = ((game.tic // 40) % 3) - 1 if p.alive else 0
        key = (p.health, p.armor, p.ammo.get(wdef.ammo, -1) if wdef.ammo else -1, tuple(sorted(p.weapons)),
               tuple(sorted(p.keys)), tuple(sorted(p.ammo.items())), p.damage_count > 0, look, p.weapon)
        if key == self._last:
            return self.canvas, False
        self._last = key
        c = self.canvas
        c.rect(0, 0, self.W, self.H, BAR)
        c.rect(0, 0, self.W, 1, rgb(120, 120, 126))
        ammo = p.ammo.get(wdef.ammo, 0) if wdef.ammo else None
        draw_text(c, str(ammo) if ammo is not None else "-", 6, 8, RED, 2)
        draw_text(c, "AMMO", 10, 24, GREY)
        draw_text(c, f"{max(p.health, 0)}%", 52, 8, RED, 2)
        draw_text(c, "HEALTH", 56, 24, GREY)
        for i in range(2, 8):                                              # ARMS: weapon slots 2..7
            owned = any(defs.weapons[w].slot == i for w in p.weapons)
            col, x, y = (rgb(240, 200, 40) if owned else rgb(120, 120, 120)), 112 + ((i - 2) % 3) * 12, 5 + ((i - 2) // 3) * 10
            draw_text(c, str(i), x, y, col)
        draw_text(c, "ARMS", 118, 25, GREY)
        draw_face(c, 148, 2, p.health, p.damage_count > 0, look)
        draw_text(c, f"{p.armor}%", 186, 8, RED, 2)
        draw_text(c, "ARMOR", 190, 24, GREY)
        for i, k in enumerate(("blue", "yellow", "red")):
            c.rect(244, 4 + i * 9, 7, 8, KEY_COLORS[k] if k in p.keys else rgb(55, 55, 58))
        for i, (name, _cap) in enumerate(sorted(defs.settings.ammo_max.items())[:4]):
            draw_text(c, f"{name[:4].upper()} {p.ammo.get(name, 0)}", 262, 3 + i * 7, rgb(220, 190, 40))
        return c, True
