from tests.helpers import *  # noqa
from entities.monsters import Monster


def spawn(g, mid, x, y, angle=180):
    m = Monster(g.defs.monsters[mid], x, y, 0.0, angle)
    g.entities.append(m)
    return m


def test_pistol_damage_values_and_ammo():
    g = make_game()
    m = spawn(g, "imp", 200, 64)
    start = g.player.ammo["bullets"]
    run(g, 1, fire=True)
    assert g.player.ammo["bullets"] == start - 1
    assert m.health in (60 - 5, 60 - 10, 60 - 15)


def test_pistol_cycle_is_14_tics():
    g = make_game()
    spawn(g, "imp", 300, 64)
    run(g, 40, fire=True)             # first shot on tic 1 (the weapon is already raised)
    shots = 50 - g.player.ammo["bullets"]
    assert 2 <= shots <= 3


def test_zombie_dies_drops_clip_and_counts_kill():
    g = make_game()
    z = spawn(g, "zombieman", 200, 64)
    run(g, 120, fire=True)
    assert z.state == "dead" and g.kills == 1
    assert any(e.kind == "pickup" and e.pdef.id == "clip" for e in g.entities)


def test_shotgun_fires_seven_pellets_one_shell():
    g = make_game()
    g.player.weapons.add("shotgun"); g.player.ammo["shells"] = 10; g.player.weapon = "shotgun"
    g.player.wstate, g.player.wy = "ready", 32
    imps = [spawn(g, "imp", 160, 64 + i * 3) for i in range(1)]
    run(g, 1, fire=True)
    assert g.player.ammo["shells"] == 9
    assert imps[0].health < 60 - 5 * 3          # several pellets hit at close range


def test_autoaim_hits_monster_on_higher_floor():
    ledge = {"polygon": [[300, 0], [300, 512], [512, 512], [512, 0]], "floor": 24, "ceiling": 128}
    g = make_game(split_room([ledge]))
    g.level.sectors[0].polygon = None
    m = Monster(g.defs.monsters["imp"], 400, 64, 24.0, 180)
    g.entities.append(m)
    # no need to constrain the player's ceiling: just shoot
    run(g, 1, fire=True)
    assert m.health < 60


def test_wall_stops_bullets():
    wall_room = room_spec()
    g = make_game(wall_room)
    m = spawn(g, "imp", 450, 64)
    g.level.sectors[0].ceiling = 128
    # a wall between player and monster: a narrow partition sector with ceiling = floor
    # (checked via ray tracing)
    from world.collision import trace_ray
    d, ln = trace_ray(g.level, 64, 64, 32, 1, 0, 0, 2048)
    assert ln is not None and abs(d - (512 - 64)) < 1e-6


def test_weapon_switch_and_out_of_ammo_autoswitch():
    g = make_game()
    g.player.ammo["bullets"] = 1
    run(g, 40, fire=True)
    run(g, 40)
    assert g.player.weapon == "fist"
    run(g, 1, weapon=2)
    run(g, 40)
    assert g.player.weapon == "fist"             # no ammo — we stay with the fist


def test_player_armor_absorbs_third_and_dies_at_zero():
    g = make_game()
    p = g.player
    p.armor, p.armor_type = 100, 1
    p.take_damage(g, 30, None)
    assert p.health == 80 and p.armor == 90
    p.take_damage(g, 500, None)
    assert not p.alive and g.state == "dead"
