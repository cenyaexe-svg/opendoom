from tests.helpers import *  # noqa
import math


def face(g, x, y, tx, ty):
    g.player.x, g.player.y = x, y
    g.player.angle = math.degrees(math.atan2(ty - y, tx - x))


def test_demo_level_secret_door_and_secret_counter():
    g = make_game(load_spec())
    g.player.x, g.player.y, g.player.angle = 30, 96, 180
    run(g, 1, use=True)
    run(g, 80)
    run(g, 40, forward=1)
    assert g.secrets == 1


def load_spec():
    import json
    return json.loads((ASSETS_DIR / "maps" / "map01.json").read_text(encoding="utf-8"))


def test_demo_level_start_door_opens():
    g = make_game(load_spec())
    face(g, 235, 96, 300, 96)
    run(g, 1, use=True)
    run(g, 60)
    assert g.level.sector_at(272, 96).ceiling > 56


def test_demo_level_red_door_requires_key_then_exit_switch_ends_level():
    g = make_game(load_spec())
    face(g, 745, 32, 800, 32)
    run(g, 1, use=True)
    assert g.level.sector_at(784, 32).ceiling == 0
    g.player.keys.add("red")
    run(g, 1)
    run(g, 1, use=True)
    run(g, 60)
    assert g.level.sector_at(784, 32).ceiling > 56
    face(g, 1100, 32, 1130, 32)
    run(g, 1, use=True)
    assert g.state == "exit"


def test_demo_level_lift_takes_player_down_and_back():
    g = make_game(load_spec())
    for e in list(g.entities):
        if e.kind in g.defs.monsters:
            e.removed = True
    g.player.x, g.player.y, g.player.angle = 128, 30, 270
    run(g, 12, forward=1)                      # crossed the lift line at y=0
    run(g, 30)
    assert g.player.z == -64                   # rode down with the floor
    run(g, 8, forward=1)                       # step off into the pit
    run(g, 250)
    assert g.level.sector_at(128, -30).floor == 0     # the lift returned to the top


def test_nukage_damages_every_32_tics():
    g = make_game(load_spec())
    for e in list(g.entities):
        if e.kind in g.defs.monsters:
            e.removed = True
    g.player.x, g.player.y = 560, 0
    g.player.z = g.player.floor_z = -16
    hp = g.player.health
    run(g, 70)
    assert g.player.health == hp - 10
