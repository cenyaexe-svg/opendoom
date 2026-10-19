"""Minimal pure-Python RGBA raster: primitive drawing for procedural textures, sprites and the HUD."""
from __future__ import annotations

import struct
import zlib

Color = tuple[int, int, int, int]


def rgb(r: int, g: int, b: int, a: int = 255) -> Color:
    return (r, g, b, a)


def shade(c: Color, k: float) -> Color:
    return (max(0, min(255, int(c[0] * k))), max(0, min(255, int(c[1] * k))), max(0, min(255, int(c[2] * k))), c[3])


class Canvas:
    def __init__(self, w: int, h: int, fill: Color = (0, 0, 0, 0)):
        self.w, self.h = w, h
        self.px: list[Color] = [fill] * (w * h)

    def set(self, x: int, y: int, c: Color) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[y * self.w + x] = c

    def get(self, x: int, y: int) -> Color:
        return self.px[(y % self.h) * self.w + (x % self.w)]

    def rect(self, x: int, y: int, w: int, h: int, c: Color) -> None:
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.set(xx, yy, c)

    def ellipse(self, cx: float, cy: float, rx: float, ry: float, c: Color) -> None:
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - rx) - 1, int(cx + rx) + 2):
                if rx > 0 and ry > 0 and ((xx + 0.5 - cx) / rx) ** 2 + ((yy + 0.5 - cy) / ry) ** 2 <= 1.0:
                    self.set(xx, yy, c)

    def poly(self, pts: list[tuple[float, float]], c: Color) -> None:
        ys = [p[1] for p in pts]
        for y in range(int(min(ys)), int(max(ys)) + 1):
            xs = []
            for i, (x1, y1) in enumerate(pts):
                x2, y2 = pts[(i + 1) % len(pts)]
                if (y1 <= y + 0.5 < y2) or (y2 <= y + 0.5 < y1):
                    xs.append(x1 + (y + 0.5 - y1) * (x2 - x1) / (y2 - y1))
            xs.sort()
            for a, b in zip(xs[0::2], xs[1::2]):
                for x in range(int(round(a)), int(round(b))):
                    self.set(x, y, c)

    def outline(self, c: Color) -> None:
        """Dark outline around the opaque area (gives sprites a hand-drawn look)."""
        src = list(self.px)
        for y in range(self.h):
            for x in range(self.w):
                if src[y * self.w + x][3] == 0:
                    for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                        nx, ny = x + dx, y + dy
                        if 0 <= nx < self.w and 0 <= ny < self.h and src[ny * self.w + nx][3] > 0:
                            self.px[y * self.w + x] = c
                            break

    def blit(self, other: "Canvas", x: int, y: int, scale: int = 1) -> None:
        for sy in range(other.h):
            for sx in range(other.w):
                c = other.px[sy * other.w + sx]
                if c[3]:
                    for oy in range(scale):
                        for ox in range(scale):
                            self.set(x + sx * scale + ox, y + sy * scale + oy, c)

    def tinted(self, t: tuple[float, float, float]) -> "Canvas":
        out = Canvas(self.w, self.h)
        out.px = [(int(c[0] * t[0]), int(c[1] * t[1]), int(c[2] * t[2]), c[3]) for c in self.px]
        return out

    def to_rgba_bytes(self) -> bytes:
        return b"".join(bytes(c) for c in self.px)

    def to_panda_ram(self) -> bytes:
        """BGRA with rows bottom-to-top — the Panda3D RAM image format."""
        rows = []
        for y in range(self.h - 1, -1, -1):
            rows.append(b"".join(bytes((c[2], c[1], c[0], c[3])) for c in self.px[y * self.w:(y + 1) * self.w]))
        return b"".join(rows)

    def to_png(self) -> bytes:
        raw = b"".join(b"\x00" + b"".join(bytes(c) for c in self.px[y * self.w:(y + 1) * self.w]) for y in range(self.h))

        def chunk(tag: bytes, data: bytes) -> bytes:
            body = tag + data
            return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

        return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 6, 0, 0, 0))
                + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
