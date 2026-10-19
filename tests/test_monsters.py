from tests.helpers import *  # noqa
from entities.monsters import Monster
from tests.test_combat import spawn


def test_monster_wakes_on_sight_and_chases():
    g = make_game()
    m = spawn(g, "zombieman", 300, 64, angle=180)      # facing the player
    run(g, 2)
    assert m.state in ("chase", "attack")


def test_monster_facing_away_does_not_notice():
    g = make_game()
    m = spawn(g, "zombieman", 300, 64, angle=0)
    run(g, 10)
    assert m.state == "idle"


def test_monster_behind_wall_stays_idle_until_noise():
    wall = {"polygon": [[200, 0], [200, 512], [232, 512], [232, 0]], "floor": 0, "ceiling": 0, "wall": "metal"}
    right = {"polygon": [[232, 0], [232, 512], [512, 512], [512, 0]], "floor": 0, "ceiling": 128}
    left_room = room_spec()
    left_room["sectors"][0]["polygon"] = [[0, 0], [0, 512], [200, 512], [200, 0]]
    left_room["sectors"] += [wall, right]
    g = make_game(left_room)
    m = spawn(g, "zombieman", 300, 64)
    run(g, 20)
    assert m.state == "idle"
    run(g, 1, fire=True)                                # the shot does not pass through the closed "door"
    assert m.state == "idle"


def test_zombieman_hurts_player_eventually():
    g = make_game()
    spawn(g, "zombieman", 200, 64)
    run(g, 700)
    assert g.player.health < 100


def test_imp_fireball_damages_player():
    g = make_game()
    imp = spawn(g, "imp", 330, 64)
    imp.angle = 180
    seen = []
    g.bus.on("sound", lambda name, x, y: seen.append(name))
    run(g, 400)
    assert "fireball" in seen and g.player.health < 100


def test_imp_melee_when_close():
    g = make_game()
    imp = spawn(g, "imp", 100, 64)
    run(g, 150)
    assert g.player.health < 100


def test_pain_interrupts_and_death_is_final():
    g = make_game()
    m = spawn(g, "imp", 200, 64)
    m.take_damage(g, 10, g.player)
    m.take_damage(g, 100, g.player)
    assert m.state == "dead" and not m.solid and not m.shootable
    hp = m.health
    m.take_damage(g, 5, g.player)
    assert m.health == hp and g.kills == 1


def test_monsters_do_not_walk_off_ledges():
    pit = {"polygon": [[300, 0], [300, 512], [512, 512], [512, 0]], "floor": -64, "ceiling": 128}
    g = make_game(split_room([pit]))
    m = spawn(g, "imp", 280, 64)
    run(g, 200)
    assert m.z == 0


def test_monster_opens_doors():
    door = {"polygon": [[200, 0], [200, 512], [232, 512], [232, 0]], "floor": 0, "ceiling": 0, "wall": "door"}
    right = {"polygon": [[232, 0], [232, 512], [512, 512], [512, 0]], "floor": 0, "ceiling": 128}
    spec = room_spec()
    spec["sectors"][0]["polygon"] = [[0, 0], [0, 512], [200, 512], [200, 0]]
    spec["sectors"] += [door, right]
    spec["line_props"] = [{"from": [232, 0], "to": [232, 512], "special": {"action": "door"}},
                          {"from": [200, 0], "to": [200, 512], "special": {"action": "door"}}]
    g = make_game(spec)
    m = spawn(g, "imp", 300, 64)
    m.wake(g)
    run(g, 300)
    assert g.level.sectors[1].ceiling > 0 or m.x < 200
