"""Procedural 64x64 wall and floor textures (pixel style, original, no third-party assets).

A custom texture can be dropped in as textures/<name>.png (in assets or in a mod) — it replaces the procedural one.
"""
from __future__ import annotations

from rendering.canvas import Canvas, rgb, shade

SIZE = 64


def _h(x: int, y: int, seed: int) -> float:
    n = (x * 374761393 + y * 668265263 + seed * 1442695041) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((n ^ (n >> 16)) & 0xFFFF) / 65535.0


def _noisy(c: Canvas, base, amount: float, seed: int) -> None:
    for y in range(c.h):
        for x in range(c.w):
            c.set(x, y, shade(base, 1.0 - amount + 2 * amount * _h(x, y, seed)))


def brick() -> Canvas:
    c = Canvas(SIZE, SIZE)
    for row in range(8):
        off = 8 if row % 2 else 0
        for col in range(-1, 5):
            x0 = col * 16 + off
            base = shade(rgb(150, 70, 50), 0.85 + 0.3 * _h(col, row, 3))
            c.rect(x0, row * 8, 15, 7, base)
            for y in range(row * 8, row * 8 + 7):
                for x in range(x0, x0 + 15):
                    c.set(x, y, shade(c.get(x, y), 0.9 + 0.2 * _h(x, y, 7)))
    for row in range(8):
        for x in range(SIZE):
            c.set(x, row * 8 + 7, rgb(60, 40, 35))
    return c


def tech() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(90, 100, 112), 0.07, 1)
    c.rect(0, 0, 64, 2, rgb(50, 56, 66)); c.rect(0, 62, 64, 2, rgb(50, 56, 66))
    for x in (0, 31, 32, 63):
        c.rect(x, 0, 1, 64, rgb(45, 50, 60))
    for px, py in ((4, 6), (58, 6), (4, 56), (58, 56)):
        c.rect(px, py, 2, 2, rgb(170, 175, 185))
    c.rect(10, 20, 20, 24, rgb(40, 60, 70))
    for i in range(5):
        c.rect(12, 23 + i * 4, 16, 2, rgb(60 + i * 30, 200 - i * 20, 90))
    c.rect(38, 14, 18, 36, rgb(70, 78, 90)); c.rect(40, 16, 14, 8, rgb(190, 60, 40))
    return c


def metal() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(110, 110, 105), 0.08, 2)
    for y in range(0, 64, 16):
        c.rect(0, y, 64, 1, rgb(60, 60, 58)); c.rect(0, y + 1, 64, 1, rgb(150, 150, 145))
    for x in range(4, 64, 16):
        for y in range(4, 64, 16):
            c.rect(x, y, 2, 2, rgb(70, 70, 66))
    return c


def door() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(120, 125, 135), 0.05, 4)
    c.rect(0, 0, 64, 4, rgb(70, 74, 82)); c.rect(0, 60, 64, 4, rgb(70, 74, 82))
    c.rect(28, 0, 8, 64, rgb(80, 85, 95)); c.rect(30, 0, 4, 64, rgb(40, 44, 52))
    for y in (10, 26, 42):
        c.rect(6, y, 18, 8, rgb(95, 100, 110)); c.rect(40, y, 18, 8, rgb(95, 100, 110))
    return c


def lock_red() -> Canvas:
    c = door()
    c.rect(26, 24, 12, 16, rgb(170, 30, 30)); c.rect(29, 28, 6, 8, rgb(240, 90, 80))
    return c


def exit_switch() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(70, 80, 70), 0.06, 5)
    c.rect(8, 10, 48, 20, rgb(20, 90, 30)); c.rect(10, 12, 44, 16, rgb(60, 220, 90))
    for i, x in enumerate((14, 22, 30, 38)):                 # stylised "EXIT" lettering made of blocks
        c.rect(x, 15, 6, 10, rgb(10, 70, 20)); c.rect(x + 2, 17, 2, 6, rgb(60, 220, 90))
    c.rect(24, 38, 16, 20, rgb(180, 180, 175)); c.rect(28, 42, 8, 12, rgb(210, 40, 40))
    return c


def step() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(130, 100, 70), 0.1, 6)
    c.rect(0, 0, 64, 3, rgb(190, 150, 100)); c.rect(0, 60, 64, 4, rgb(70, 50, 35))
    return c


def lift() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(100, 100, 40), 0.06, 8)
    for i in range(-64, 64, 16):
        c.poly([(i, 0), (i + 8, 0), (i + 72, 64), (i + 64, 64)], rgb(30, 30, 25))
    return c


def tile() -> Canvas:
    c = Canvas(SIZE, SIZE)
    for ty in range(2):
        for tx in range(2):
            c.rect(tx * 32, ty * 32, 31, 31, shade(rgb(105, 105, 110), 0.9 + 0.2 * _h(tx, ty, 9)))
    for y in range(64):
        for x in range(64):
            c.set(x, y, shade(c.get(x, y) if c.get(x, y)[3] else rgb(40, 40, 44), 0.95 + 0.1 * _h(x, y, 10)))
    c.rect(31, 0, 1, 64, rgb(40, 40, 44)); c.rect(0, 31, 64, 1, rgb(40, 40, 44))
    c.rect(63, 0, 1, 64, rgb(40, 40, 44)); c.rect(0, 63, 64, 1, rgb(40, 40, 44))
    return c


def stone() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(95, 85, 70), 0.15, 11)
    return c


def panel() -> Canvas:
    c = Canvas(SIZE, SIZE)
    _noisy(c, rgb(70, 74, 82), 0.05, 12)
    c.rect(0, 0, 64, 1, rgb(30, 32, 38)); c.rect(0, 0, 1, 64, rgb(30, 32, 38))
    c.rect(24, 24, 16, 16, rgb(220, 225, 200)); c.rect(26, 26, 12, 12, rgb(250, 252, 235))
    return c


def nukage() -> Canvas:
    c = Canvas(SIZE, SIZE)
    for y in range(64):
        for x in range(64):
            v = 0.55 + 0.45 * _h(x // 3, y // 3, 13)
            c.set(x, y, rgb(int(40 * v), int(210 * v), int(40 * v)))
    return c


GENERATORS = {f.__name__: f for f in (brick, tech, metal, door, lock_red, exit_switch, step, lift, tile,
                                       stone, panel, nukage)}
TEXTURE_NAMES = set(GENERATORS)


def make_texture(name: str) -> Canvas:
    gen = GENERATORS.get(name)
    return gen() if gen else _missing()


def _missing() -> Canvas:
    c = Canvas(SIZE, SIZE, rgb(255, 0, 255))
    c.rect(0, 0, 32, 32, rgb(0, 0, 0)); c.rect(32, 32, 32, 32, rgb(0, 0, 0))
    return c
