from tests.helpers import *  # noqa
from world.builder import build_from_polygons
from world.geometry import signed_area, triangulate
from world.level_loader import LevelError


def test_triangulate_concave_area():
    l_shape = [(0, 0), (0, 100), (50, 100), (50, 50), (100, 50), (100, 0)]
    tris = triangulate(l_shape)
    total = sum(abs(signed_area(list(t))) for t in tris)
    assert abs(total - abs(signed_area(l_shape))) < 1e-6


def test_builder_makes_two_sided_line_with_t_junction():
    spec = {"sectors": [
        {"polygon": [[0, 0], [0, 100], [100, 100], [100, 0]], "floor": 0, "ceiling": 100},
        {"polygon": [[100, 20], [100, 60], [150, 60], [150, 20]], "floor": 0, "ceiling": 80}]}
    out = build_from_polygons(spec)
    two_sided = [ln for ln in out["linedefs"] if ln["back"] is not None]
    assert len(two_sided) == 1
    assert len(out["linedefs"]) == 4 + 3 + 2   # room: 4+2 (split), corridor: 3 + shared


def test_builder_rejects_overlap():
    spec = {"sectors": [
        {"polygon": [[0, 0], [0, 10], [10, 10], [10, 0]], "floor": 0, "ceiling": 10},
        {"polygon": [[0, 0], [0, 10], [10, 10], [10, 0]], "floor": 0, "ceiling": 10}]}
    with expect_error(ValueError):
        build_from_polygons(spec)


def test_level_requires_player_start():
    spec = room_spec()
    spec["things"] = []
    with expect_error(LevelError):
        load_level(spec)


def test_sector_at_and_demo_level():
    lv = load_level(ASSETS_DIR / "maps" / "map01.json")
    assert lv.sector_at(128, 96).id == 0
    assert lv.sector_at(-5000, 0) is None
    for t in lv.things:
        assert lv.sector_at(t.x, t.y) is not None, t


def test_sector_at_inside_notch_belongs_to_pool():
    lv = load_level(ASSETS_DIR / "maps" / "map01.json")
    assert lv.sector_at(560, 0).floor == -16          # the nukage pool is a notch cut into the hall
    assert lv.sector_at(560, 100).floor == 0
