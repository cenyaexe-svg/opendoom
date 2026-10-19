"""Procedural sprites for monsters, items, weapons and effects (1 pixel = 1 world unit).

Monsters: <name>_A (idle), B/C (walk), D (attack), E (pain), F (corpse).
Held weapons: <name>_ready / <name>_fire. An unknown name yields a conspicuous "?" sprite.
Custom sprite: a PNG sprites/<name>.png in assets or in a mod replaces the procedural one.
"""
from __future__ import annotations

from rendering.canvas import Canvas, rgb, shade

OUT = rgb(18, 12, 12)


def _humanoid(skin, cloth, pose: str, imp: bool) -> Canvas:
    c = Canvas(48, 60)
    lean = -3 if pose == "E" else 0
    step = {"B": 3, "C": -3}.get(pose, 0)
    c.rect(17 + step, 38, 6, 20, shade(cloth, 0.7)); c.rect(26 - step, 38, 6, 20, shade(cloth, 0.7))
    c.rect(16 + step, 56, 8, 3, rgb(40, 30, 25)); c.rect(25 - step, 56, 8, 3, rgb(40, 30, 25))
    c.rect(15 + lean, 18, 20, 22, cloth)
    arm_y = 8 if pose == "D" else 20
    c.rect(8 + lean, arm_y, 6, 18, skin); c.rect(35 + lean, arm_y + (0 if pose == "D" else 2), 6, 18, skin)
    c.ellipse(25 + lean, 12, 8, 9, skin)
    eyes = rgb(255, 60, 20) if imp else rgb(20, 20, 20)
    c.rect(21 + lean, 10, 2, 2, eyes); c.rect(27 + lean, 10, 2, 2, eyes)
    if pose in ("D", "E"):
        c.rect(23 + lean, 16, 5, 3, rgb(90, 10, 10))
    if imp:
        c.poly([(18 + lean, 6), (20 + lean, 0), (23 + lean, 5)], rgb(230, 220, 190))
        c.poly([(27 + lean, 5), (30 + lean, 0), (32 + lean, 6)], rgb(230, 220, 190))
        for sx in (17, 22, 27):
            c.poly([(sx + lean, 20), (sx + 2 + lean, 14), (sx + 4 + lean, 20)], shade(skin, 0.75))
        if pose == "D":
            c.ellipse(11 + lean, 6, 5, 5, rgb(255, 170, 40))
    else:
        c.rect(30 + lean, 24 + (0 if pose != "D" else -12), 16, 4, rgb(60, 60, 64))   # rifle
        c.rect(14 + lean, 14, 22, 4, shade(cloth, 0.8))
        c.rect(19 + lean, 2, 12, 6, rgb(110, 85, 50))                                   # hair/helmet
    c.outline(OUT)
    return c


def _corpse(skin, cloth) -> Canvas:
    c = Canvas(56, 16)
    c.rect(4, 6, 30, 8, cloth); c.ellipse(40, 10, 8, 6, skin); c.rect(14, 3, 10, 5, skin)
    c.rect(44, 11, 8, 3, rgb(120, 20, 20)); c.ellipse(26, 14, 14, 2, rgb(110, 15, 15))
    c.outline(OUT)
    return c


def monster_frame(base: str, frame: str) -> Canvas:
    imp = base == "imp"
    skin, cloth = (rgb(150, 95, 55), rgb(120, 70, 40)) if imp else (rgb(200, 150, 120), rgb(75, 100, 60))
    return _corpse(skin, cloth) if frame == "F" else _humanoid(skin, cloth, frame, imp)


def _box(w, h, main, accent, symbol=None) -> Canvas:
    c = Canvas(w, h)
    c.rect(0, 0, w, h, main); c.rect(0, 0, w, 2, shade(main, 1.3)); c.rect(0, h - 2, w, 2, shade(main, 0.6))
    if symbol == "cross":
        c.rect(w // 2 - 2, 3, 4, h - 6, accent); c.rect(3, h // 2 - 2, w - 6, 4, accent)
    elif symbol == "stripe":
        c.rect(0, h // 2 - 2, w, 4, accent)
    c.outline(OUT)
    return c


def _key(color) -> Canvas:
    c = Canvas(12, 18)
    c.rect(2, 0, 8, 18, color); c.rect(4, 3, 4, 4, shade(color, 0.5)); c.rect(0, 8, 12, 2, shade(color, 1.3))
    c.outline(OUT)
    return c


def _gun_side(w, h, body, barrel) -> Canvas:
    c = Canvas(w, h)
    c.rect(0, h // 2 - 3, w, 6, barrel); c.rect(w // 3, h // 2 - 2, w // 2, 8, body); c.rect(2, h // 2 + 3, 6, 6, shade(body, 0.7))
    c.outline(OUT)
    return c


def _blob(r, outer, inner) -> Canvas:
    c = Canvas(2 * r, 2 * r)
    c.ellipse(r, r, r, r, outer); c.ellipse(r, r, r * 0.6, r * 0.6, inner)
    return c


def _weapon(name: str, fire: bool) -> Canvas:
    c = Canvas(80, 64)
    skin = rgb(210, 160, 125)
    flash = rgb(255, 230, 120)
    if name == "fist":
        x = 30 if not fire else 26
        y = 22 if not fire else 6
        c.rect(x, y, 26, 44 + 14 - (y - 6) // 2, skin); c.rect(x + 2, y + 2, 22, 5, shade(skin, 1.15))
        for i in range(3):
            c.rect(x + 3 + i * 7, y, 1, 7, shade(skin, 0.6))
        c.rect(x - 2, y + 28, 30, 30, rgb(80, 80, 55))
    else:
        dark, mid = rgb(60, 60, 66), rgb(110, 110, 118)
        if name == "pistol":
            c.rect(34, 18, 14, 46, mid); c.rect(35, 14, 12, 8, dark); c.rect(38, 24, 6, 40, shade(mid, 0.8))
            c.rect(31, 50, 20, 14, skin)
        elif name == "shotgun":
            c.rect(32, 10, 8, 54, rgb(70, 70, 75)); c.rect(41, 10, 8, 54, rgb(85, 85, 90))
            c.rect(29, 34, 22, 14, rgb(120, 80, 45)); c.rect(26, 48, 28, 16, skin)
        else:                                                           # chaingun
            for i in range(3):
                c.rect(28 + i * 9, 6, 7, 40, shade(mid, 0.8 + i * 0.15))
            c.rect(24, 40, 32, 22, dark); c.rect(22, 54, 36, 10, skin)
        if fire:
            c.poly([(40, -2), (28, 8), (34, 6), (40, 14), (46, 6), (52, 8)], flash)
            c.ellipse(40, 6, 6, 6, rgb(255, 255, 220))
    if not fire or name == "fist":
        pass
    c.outline(OUT)
    return c


def make_sprite(name: str) -> Canvas:
    base, _, frame = name.rpartition("_")
    if base in ("zombieman", "imp") and frame in tuple("ABCDEF"):
        return monster_frame(base, frame)
    if ":" in name:                                                     # "<weapon>:<frame>"
        w, f = name.split(":")
        if w in ("fist", "pistol", "shotgun", "chaingun"):
            return _weapon(w, f == "fire")
    table = {
        "medikit": lambda: _box(22, 14, rgb(235, 235, 235), rgb(210, 30, 30), "cross"),
        "stimpack": lambda: _box(14, 10, rgb(225, 225, 225), rgb(210, 30, 30), "cross"),
        "health_bonus": lambda: _blob(5, rgb(40, 60, 220), rgb(140, 170, 255)),
        "armor_bonus": lambda: _box(10, 12, rgb(40, 70, 200), rgb(150, 190, 255), "stripe"),
        "green_armor": lambda: _box(26, 18, rgb(40, 150, 50), rgb(130, 230, 120), "stripe"),
        "blue_armor": lambda: _box(26, 18, rgb(40, 70, 200), rgb(150, 190, 255), "stripe"),
        "clip": lambda: _box(10, 14, rgb(170, 150, 60), rgb(90, 75, 30), "stripe"),
        "shells": lambda: _box(18, 14, rgb(180, 50, 40), rgb(240, 200, 80), "stripe"),
        "shotgun_pickup": lambda: _gun_side(30, 14, rgb(120, 80, 45), rgb(85, 85, 90)),
        "chaingun_pickup": lambda: _gun_side(30, 16, rgb(70, 70, 76), rgb(120, 120, 128)),
        "key_red": lambda: _key(rgb(220, 40, 40)), "key_blue": lambda: _key(rgb(50, 80, 230)),
        "key_yellow": lambda: _key(rgb(240, 210, 40)),
        "fireball": lambda: _blob(8, rgb(220, 90, 20), rgb(255, 230, 120)),
        "fireball_hit": lambda: _blob(14, rgb(230, 100, 30), rgb(255, 220, 100)),
        "plasma": lambda: _blob(7, rgb(40, 110, 255), rgb(200, 235, 255)),
        "plasma_hit": lambda: _blob(12, rgb(50, 120, 255), rgb(210, 240, 255)),
        "puff": lambda: _blob(4, rgb(190, 190, 190), rgb(240, 240, 240)),
        "blood": lambda: _blob(5, rgb(150, 10, 10), rgb(210, 40, 30)),
    }
    if name in table:
        return table[name]()
    c = Canvas(16, 16, rgb(255, 0, 255))
    c.rect(5, 3, 6, 2, rgb(0, 0, 0)); c.rect(9, 5, 2, 4, rgb(0, 0, 0)); c.rect(7, 8, 2, 2, rgb(0, 0, 0)); c.rect(7, 12, 2, 2, rgb(0, 0, 0))
    return c
