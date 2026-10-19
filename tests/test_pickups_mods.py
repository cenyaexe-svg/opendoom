import json, tempfile
from pathlib import Path
from tests.helpers import *  # noqa
from entities.base import Pickup
from gameplay import pickups
from modding.definitions import DefinitionError, parse_all
from modding.mod_loader import (ModError, discover_mods, load_game_data, resolve_order, run_mod_scripts)
from config import MODS_DIR


def give(g, pid):
    p = Pickup(g.defs.pickups[pid], g.player.x, g.player.y, 0)
    g.entities.append(p)
    return pickups.try_pickup(g, g.player, p), p


def test_stimpack_left_at_full_health_and_used_when_hurt():
    g = make_game()
    ok, p = give(g, "stimpack")
    assert not ok and not p.removed
    g.player.health = 50
    ok, p = give(g, "stimpack")
    assert ok and g.player.health == 60 and p.removed


def test_health_bonus_exceeds_100_up_to_200():
    g = make_game()
    g.player.health = 199
    assert give(g, "health_bonus")[0] and g.player.health == 200
    assert not give(g, "health_bonus")[0]


def test_ammo_capped_and_refused_when_full():
    g = make_game()
    g.player.ammo["bullets"] = 195
    assert give(g, "clip")[0] and g.player.ammo["bullets"] == 200
    assert not give(g, "clip")[0]


def test_armor_types():
    g = make_game()
    assert give(g, "armor_bonus")[0] and g.player.armor == 1 and g.player.armor_type == 1
    assert give(g, "green_armor")[0] and g.player.armor == 100
    assert not give(g, "green_armor")[0]
    assert give(g, "blue_armor")[0] and g.player.armor_type == 2


def test_weapon_pickup_gives_ammo_and_switches():
    g = make_game()
    assert give(g, "shotgun")[0]
    assert "shotgun" in g.player.weapons and g.player.ammo["shells"] == 8 and g.player.pending == "shotgun"
    run(g, 60)
    assert g.player.weapon == "shotgun"


def test_key_pickup_once():
    g = make_game()
    assert give(g, "key_red")[0] and "red" in g.player.keys
    assert not give(g, "key_red")[0]


def test_walking_over_pickup_collects_it():
    g = make_game(room_spec(things=[{"type": "stimpack", "x": 200, "y": 64}]))
    g.player.health = 40
    run(g, 20, forward=1)
    assert g.player.health == 50 and g.items == 1


def test_example_mod_overrides_and_adds_content():
    mods = discover_mods(MODS_DIR)
    defs, _ = load_game_data(ASSETS_DIR, resolve_order(["example_mod"], mods))
    assert defs.monsters["imp"].health == 90 and defs.monsters["imp"].speed == 10
    assert defs.monsters["imp"].name == "Imp"                     # the other fields are untouched
    assert defs.pickups["medikit"].params["amount"] == 50
    assert "plasma_pistol" in defs.weapons and defs.settings.ammo_max["cells"] == 300
    assert defs.settings.ammo_max["bullets"] == 200               # dictionaries are merged
    g = make_game(defs=defs)
    assert "plasma_pistol" in g.player.weapons


def test_plasma_pistol_fires_projectile():
    mods = discover_mods(MODS_DIR)
    defs, _ = load_game_data(ASSETS_DIR, resolve_order(["example_mod"], mods))
    g = make_game(defs=defs)
    from tests.test_combat import spawn
    m = spawn(g, "imp", 400, 64)
    g.player.weapon, g.player.wstate, g.player.wy = "plasma_pistol", "ready", 32
    run(g, 1, fire=True)
    assert g.player.ammo["cells"] == 119
    run(g, 40)
    assert m.health < 90


def test_mod_load_order_dependencies_and_cycles():
    from modding.mod_loader import ModManifest
    mk = lambda i, pr, dep=(): ModManifest(i, i, "1", pr, list(dep), None, Path("."))
    avail = {"a": mk("a", 300), "b": mk("b", 100, ["a"]), "c": mk("c", 200)}
    assert [m.id for m in resolve_order(["b", "c"], avail)] == ["c", "a", "b"] or \
           [m.id for m in resolve_order(["b", "c"], avail)] == ["a", "b", "c"]
    order = [m.id for m in resolve_order(["b"], avail)]
    assert order.index("a") < order.index("b")
    with expect_error(ModError):
        resolve_order(["zzz"], avail)
    cyc = {"x": mk("x", 1, ["y"]), "y": mk("y", 1, ["x"])}
    with expect_error(ModError):
        resolve_order(["x"], cyc)


def test_invalid_definitions_give_clear_errors():
    raw = json.loads((ASSETS_DIR / "defs" / "weapons.json").read_text(encoding="utf-8"))
    base = {c: json.loads((ASSETS_DIR / "defs" / f"{c}.json").read_text(encoding="utf-8"))
            for c in ("weapons", "monsters", "projectiles", "pickups", "settings")}
    bad = json.loads(json.dumps(base)); bad["weapons"]["pistol"]["dmage"] = [5, 3]
    with expect_error(DefinitionError):
        parse_all(bad)
    bad = json.loads(json.dumps(base)); bad["weapons"]["pistol"]["ammo"] = "plutonium"
    with expect_error(DefinitionError):
        parse_all(bad)
    bad = json.loads(json.dumps(base)); bad["monsters"]["imp"]["health"] = "a lot"
    with expect_error(DefinitionError):
        parse_all(bad)
    bad = json.loads(json.dumps(base)); del bad["pickups"]["clip"]
    with expect_error(DefinitionError):
        parse_all(bad)                                           # the zombieman drops a clip


def test_mod_scripts_run_only_when_called_and_register_pickup_type():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "scripted"
        root.mkdir()
        (root / "mod.json").write_text(json.dumps({"id": "scripted", "script": "script.py"}), encoding="utf-8")
        (root / "script.py").write_text(
            "def register(api):\n    api.register_pickup_type('poison', lambda game, player, d: False)\n"
            "    api.on('monster_killed', lambda game, monster: None)\n", encoding="utf-8")
        mods = discover_mods(Path(d))
        order = resolve_order(["scripted"], mods)
        assert "poison" not in pickups.HANDLERS            # without calling run_mod_scripts the code is not executed
        from modding.api import ModAPI
        g = make_game()
        run_mod_scripts(order, ModAPI(g.bus, g.defs))
        assert "poison" in pickups.HANDLERS
        del pickups.HANDLERS["poison"]


def test_removing_entry_with_remove_flag():
    with tempfile.TemporaryDirectory() as d:
        root = Path(d) / "rm"
        (root / "defs").mkdir(parents=True)
        (root / "mod.json").write_text(json.dumps({"id": "rm"}), encoding="utf-8")
        (root / "defs" / "pickups.json").write_text(json.dumps({"key_blue": {"_remove": True}}), encoding="utf-8")
        defs, _ = load_game_data(ASSETS_DIR, resolve_order(["rm"], discover_mods(Path(d))))
        assert "key_blue" not in defs.pickups
