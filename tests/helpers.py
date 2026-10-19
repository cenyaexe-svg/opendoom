"""Shared test helpers (no pytest dependency)."""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from config import ASSETS_DIR  # noqa: E402
from gameplay.game import Game  # noqa: E402
from gameplay.player import TicCommand  # noqa: E402
from modding.mod_loader import load_game_data  # noqa: E402
from world.level_loader import load_level  # noqa: E402


def base_defs():
    return load_game_data(ASSETS_DIR, [])[0]


def room_spec(extra_sectors=(), things=(), line_props=(), size=512):
    """A single size x size room (sector 0) plus extra sectors and things."""
    sectors = [{"polygon": [[0, 0], [0, size], [size, size], [size, 0]], "floor": 0, "ceiling": 128,
                "wall": "tech"}] + list(extra_sectors)
    return {"name": "test", "sectors": sectors, "line_props": list(line_props),
            "things": [{"type": "player_start", "x": 64, "y": 64, "angle": 0}] + list(things)}


def split_room(extra_sectors, x=300, **kw):
    """Room 0..x (instead of 512) so that annexes starting at x do not overlap it."""
    spec = room_spec(extra_sectors, **kw)
    spec["sectors"][0]["polygon"] = [[0, 0], [0, 512], [x, 512], [x, 0]]
    return spec


def make_game(spec=None, defs=None, seed=1):
    g = Game(defs or base_defs(), load_level(spec or room_spec()), seed=seed)
    g.player.wstate, g.player.wy = "ready", 32.0      # weapon already raised
    return g


def run(game, tics, **cmd):
    for _ in range(tics):
        game.tick(TicCommand(**cmd))


def monsters(game):
    return [e for e in game.entities if e.kind in game.defs.monsters]


@contextmanager
def expect_error(exc):
    try:
        yield
    except exc:
        return
    raise AssertionError(f"Expected exception {exc.__name__}")
