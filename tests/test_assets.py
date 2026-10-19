from tests.helpers import *  # noqa
from config import MODS_DIR
from modding.mod_loader import discover_mods, resolve_order
from rendering.canvas import rgb
from rendering.meshgen import line_mesh, sector_mesh
from rendering.sprites import make_sprite
from rendering.textures import TEXTURE_NAMES
from ui.hud import StatusBar


def _is_fallback(c):
    return (c.w, c.h) == (16, 16) and c.get(0, 0) == rgb(255, 0, 255)


def _all_defs():
    yield base_defs()
    yield load_game_data(ASSETS_DIR, resolve_order(["example_mod"], discover_mods(MODS_DIR)))[0]


def test_every_sprite_in_definitions_exists():
    for d in _all_defs():
        names = [p.sprite for p in d.pickups.values()]
        names += [f"{m.sprite}_{f}" for m in d.monsters.values() for f in "ABCDEF"]
        names += [n for pr in d.projectiles.values() for n in (pr.sprite, pr.explosion_sprite)]
        names += [f"{w.sprite}:{f}" for w in d.weapons.values() for f in ("ready", "fire")]
        names += ["puff", "blood"]
        missing = [n for n in names if _is_fallback(make_sprite(n))]
        assert not missing, missing


def test_demo_map_uses_only_known_textures_and_meshes_build():
    lv = load_level(ASSETS_DIR / "maps" / "map01.json")
    used = set()
    for ln in lv.linedefs:
        used |= set(line_mesh(lv, ln))
    for s in lv.sectors:
        used |= set(sector_mesh(s))
    assert used <= TEXTURE_NAMES, used - TEXTURE_NAMES


def test_status_bar_renders_and_caches():
    g = make_game()
    bar = StatusBar()
    _, changed = bar.render(g)
    _, changed2 = bar.render(g)
    assert changed and not changed2
    g.player.health = 0
    assert bar.render(g)[1]
