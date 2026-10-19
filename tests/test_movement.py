import math
from tests.helpers import *  # noqa


def test_terminal_speed_matches_doom():
    g = make_game(room_spec(size=4096))
    run(g, 80, forward=1)
    x0 = g.player.x
    run(g, 1, forward=1)
    assert abs((g.player.x - x0) - 16.67) < 0.05      # 1.5625 / (1 - 0.90625): Doom running speed, units/tic


def test_friction_stops_player():
    g = make_game(room_spec(size=4096))
    run(g, 20, forward=1)
    run(g, 80)
    assert g.player.mx == 0 and g.player.my == 0


def test_diagonal_strafe_run_is_faster():
    g = make_game(room_spec(size=4096))
    g.player.x = g.player.y = 2000
    run(g, 80, forward=1, strafe=1)
    x0, y0 = g.player.x, g.player.y
    run(g, 1, forward=1, strafe=1)
    assert math.hypot(g.player.x - x0, g.player.y - y0) > 20.0     # "SR50": thrusts add up, ≈21.3


def test_wall_blocks_and_slides():
    g = make_game()
    g.player.x, g.player.y, g.player.angle = 400, 300, 45
    run(g, 40, forward=1)
    assert g.player.x <= 512 - 16 + 0.01 and g.player.y <= 512 - 16 + 0.01
    assert g.player.x > 450 or g.player.y > 450             # pressed against the wall and sliding along it


def test_step_height_rules():
    low = {"polygon": [[512, 0], [512, 512], [768, 512], [768, 0]], "floor": 16, "ceiling": 128}
    g = make_game(room_spec([low]))
    g.player.x, g.player.y = 400, 256
    run(g, 20, forward=1)
    assert g.player.x > 530 and g.player.z == 16            # a 16-unit step is passable
    high = dict(low, floor=40)
    g2 = make_game(room_spec([high]))
    g2.player.x, g2.player.y = 400, 256
    run(g2, 20, forward=1)
    assert g2.player.x < 512 - 15 and g2.player.z == 0      # 40 > 24: impassable


def test_fall_from_ledge_uses_gravity():
    pit = {"polygon": [[512, 0], [512, 512], [768, 512], [768, 0]], "floor": -64, "ceiling": 128}
    g = make_game(room_spec([pit]))
    g.player.x, g.player.y = 400, 256
    run(g, 30, forward=1)
    run(g, 20)
    assert g.player.z == -64


def test_closed_door_blocks_and_use_opens_it():
    door = {"polygon": [[512, 192], [512, 320], [544, 320], [544, 192]], "floor": 0, "ceiling": 0, "wall": "door"}
    beyond = {"polygon": [[544, 192], [544, 320], [800, 320], [800, 192]], "floor": 0, "ceiling": 128}
    props = [{"from": [512, 192], "to": [512, 320], "special": {"action": "door"}},
             {"from": [544, 192], "to": [544, 320], "special": {"action": "door"}}]
    g = make_game(room_spec([door, beyond], line_props=props))
    g.player.x, g.player.y = 480, 256
    run(g, 15, forward=1)
    assert g.player.x < 512                                  # the door is closed
    g.player.x = 480
    run(g, 1, use=True)
    run(g, 60)
    assert g.level.sectors[1].ceiling > 80                   # it opened
    run(g, 5, forward=1)
    run(g, 30, forward=1)
    assert g.player.x > 560
    run(g, 200)
    assert g.level.sectors[1].ceiling == 0 or g.level.sectors[1].ceiling < 128   # closes (if the player is not in the doorway)


def test_door_does_not_crush_player_standing_in_it():
    door = {"polygon": [[512, 192], [512, 320], [544, 320], [544, 192]], "floor": 0, "ceiling": 0, "wall": "door"}
    beyond = {"polygon": [[544, 192], [544, 320], [800, 320], [800, 192]], "floor": 0, "ceiling": 128}
    props = [{"from": [512, 192], "to": [512, 320], "special": {"action": "door"}}]
    g = make_game(room_spec([door, beyond], line_props=props))
    g.player.x, g.player.y = 480, 256
    run(g, 1, use=True)
    run(g, 60)
    g.player.x = 528                                         # standing in the doorway
    run(g, 400)
    assert g.level.sectors[1].ceiling > 56                   # the door did not crush
    assert g.player.alive


def test_key_door_needs_key():
    door = {"polygon": [[512, 192], [512, 320], [544, 320], [544, 192]], "floor": 0, "ceiling": 0, "wall": "lock_red"}
    beyond = {"polygon": [[544, 192], [544, 320], [800, 320], [800, 192]], "floor": 0, "ceiling": 128}
    props = [{"from": [512, 192], "to": [512, 320], "special": {"action": "door", "key": "red"}}]
    g = make_game(room_spec([door, beyond], line_props=props))
    msgs = []
    g.bus.on("message", lambda text: msgs.append(text))
    g.player.x, g.player.y = 490, 256
    run(g, 1, use=True)
    run(g, 5)
    assert g.level.sectors[1].ceiling == 0 and msgs and "red" in msgs[0]
    g.player.keys.add("red")
    run(g, 1)                                                # release use
    run(g, 1, use=True)
    run(g, 5)
    assert g.level.sectors[1].ceiling > 0


def test_lift_walk_trigger_lowers_and_returns():
    lift = {"polygon": [[512, 192], [512, 320], [640, 320], [640, 192]], "floor": 0, "ceiling": 128, "tag": 1}
    pit = {"polygon": [[640, 192], [640, 320], [800, 320], [800, 192]], "floor": -64, "ceiling": 128}
    props = [{"from": [512, 192], "to": [512, 320], "special": {"action": "lift", "trigger": "walk", "tag": 1}}]
    g = make_game(room_spec([lift, pit], line_props=props))
    g.player.x, g.player.y = 480, 256
    run(g, 6, forward=1)
    run(g, 40)
    assert g.level.sectors[1].floor == -64
    run(g, 200)
    assert g.level.sectors[1].floor == 0
