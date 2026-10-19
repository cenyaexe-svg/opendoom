"""Typed definitions of weapons, monsters, projectiles, pickups and settings.

Definitions are read from JSON (assets/defs/*.json and mods' defs/*.json). Validation is strict:
an unknown field or wrong type raises DefinitionError with the location (typos show up immediately).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


class DefinitionError(ValueError):
    pass


@dataclass(frozen=True)
class Dice:
    """Doom-style damage: mult * (1..die). Pistol: [5, 3] gives 5, 10 or 15."""
    mult: int
    die: int

    def roll(self, rng) -> int:
        return self.mult * rng.randint(1, self.die)


class _Reader:
    def __init__(self, data: dict, where: str):
        if not isinstance(data, dict):
            raise DefinitionError(f"{where}: expected an object")
        self.d, self.where, self.used = data, where, set()

    def get(self, key: str, typ, default: Any = ...):
        self.used.add(key)
        if key not in self.d:
            if default is ...:
                raise DefinitionError(f"{self.where}: missing required field '{key}'")
            return default
        v = self.d[key]
        if v is None and default is None:
            return None
        if typ is float and isinstance(v, int) and not isinstance(v, bool):
            v = float(v)
        if not isinstance(v, typ) or (typ is int and isinstance(v, bool)):
            raise DefinitionError(f"{self.where}: field '{key}' must be {typ.__name__}, not {v!r}")
        return v

    def dice(self, key: str, default: Any = ...) -> Dice | None:
        v = self.get(key, list, default)
        if v is None:
            return None
        if len(v) != 2 or not all(isinstance(i, int) and i > 0 for i in v):
            raise DefinitionError(f"{self.where}: '{key}' must be [multiplier, die], e.g. [5, 3]")
        return Dice(v[0], v[1])

    def done(self) -> None:
        extra = [k for k in self.d if k not in self.used and not k.startswith("_")]
        if extra:
            raise DefinitionError(f"{self.where}: unknown fields {extra} (typo?)")


@dataclass(frozen=True)
class ProjectileDef:
    id: str
    sprite: str
    explosion_sprite: str
    speed: float
    radius: float
    damage: Dice
    sound_launch: str | None
    sound_hit: str | None
    tint: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class WeaponDef:
    id: str
    name: str
    slot: int
    ammo: str | None
    ammo_per_shot: int
    cycle_tics: int                  # tics between shots
    damage: Dice
    pellets: int
    spread_deg: float                # spread (triangular distribution, as in Doom)
    accurate_first_shot: bool        # first shot is accurate (pistol, chaingun)
    range: float
    melee: bool
    projectile: str | None
    sprite: str
    flash_tics: int
    sound: str | None
    noisy: bool                      # wakes monsters
    tint: tuple[float, float, float] | None = None


@dataclass(frozen=True)
class MonsterDef:
    id: str
    name: str
    sprite: str
    health: int
    speed: float                     # step in units...
    move_interval: int               # ...every move_interval tics
    radius: float
    height: float
    pain_chance: int                 # out of 256
    pain_tics: int
    death_tics: int
    melee_damage: Dice | None
    missile: str | None              # "hitscan" | "projectile" | None
    missile_damage: Dice | None
    missile_projectile: str | None
    windup_tics: int
    recovery_tics: int
    sight_sound: str | None
    pain_sound: str | None
    death_sound: str | None
    attack_sound: str | None
    drop: str | None


@dataclass(frozen=True)
class PickupDef:
    id: str
    type: str                        # health | armor | ammo | weapon | key | (a type from a mod)
    sprite: str
    message: str
    sound: str
    count_item: bool
    params: dict                     # remaining fields go to the type handler


@dataclass(frozen=True)
class PlayerStart:
    health: int
    armor: int
    weapons: tuple[str, ...]
    ammo: dict


@dataclass(frozen=True)
class Settings:
    always_run: bool
    mouse_sensitivity: float
    start_map: str
    ammo_max: dict
    player_start: PlayerStart


@dataclass
class Definitions:
    weapons: dict[str, WeaponDef] = field(default_factory=dict)
    monsters: dict[str, MonsterDef] = field(default_factory=dict)
    projectiles: dict[str, ProjectileDef] = field(default_factory=dict)
    pickups: dict[str, PickupDef] = field(default_factory=dict)
    settings: Settings | None = None


BUILTIN_PICKUP_PARAMS = {
    "health": {"amount", "max"},
    "armor": {"amount", "armor_type", "max"},
    "ammo": {"ammo", "amount"},
    "weapon": {"weapon", "ammo_amount"},
    "key": {"key"},
}


def _tint(r: _Reader):
    t = r.get("tint", list, None)
    if t is None:
        return None
    if len(t) != 3 or not all(isinstance(c, (int, float)) for c in t):
        raise DefinitionError(f"{r.where}: tint must be [r, g, b] in the range 0..1")
    return tuple(float(c) for c in t)


def parse_projectile(pid: str, d: dict) -> ProjectileDef:
    r = _Reader(d, f"projectile '{pid}'")
    p = ProjectileDef(pid, r.get("sprite", str), r.get("explosion_sprite", str), r.get("speed", float),
                      r.get("radius", float, 6.0), r.dice("damage"), r.get("sound_launch", str, None),
                      r.get("sound_hit", str, None), _tint(r))
    r.done()
    return p


def parse_weapon(wid: str, d: dict) -> WeaponDef:
    r = _Reader(d, f"weapon '{wid}'")
    w = WeaponDef(wid, r.get("name", str), r.get("slot", int), r.get("ammo", str, None),
                  r.get("ammo_per_shot", int, 1), r.get("cycle_tics", int), r.dice("damage"),
                  r.get("pellets", int, 1), r.get("spread_deg", float, 5.625),
                  r.get("accurate_first_shot", bool, True), r.get("range", float, 2048.0),
                  r.get("melee", bool, False), r.get("projectile", str, None), r.get("sprite", str),
                  r.get("flash_tics", int, 4), r.get("sound", str, None), r.get("noisy", bool, True), _tint(r))
    r.done()
    if w.cycle_tics < 1 or w.pellets < 1:
        raise DefinitionError(f"weapon '{wid}': cycle_tics and pellets must be >= 1")
    return w


def parse_monster(mid: str, d: dict) -> MonsterDef:
    r = _Reader(d, f"monster '{mid}'")
    m = MonsterDef(mid, r.get("name", str), r.get("sprite", str), r.get("health", int), r.get("speed", float),
                   r.get("move_interval", int, 3), r.get("radius", float, 20.0), r.get("height", float, 56.0),
                   r.get("pain_chance", int, 0), r.get("pain_tics", int, 6), r.get("death_tics", int, 20),
                   r.dice("melee_damage", None), r.get("missile", str, None), r.dice("missile_damage", None),
                   r.get("missile_projectile", str, None), r.get("windup_tics", int, 10),
                   r.get("recovery_tics", int, 8), r.get("sight_sound", str, None),
                   r.get("pain_sound", str, None), r.get("death_sound", str, None),
                   r.get("attack_sound", str, None), r.get("drop", str, None))
    r.done()
    if m.health < 1 or m.move_interval < 1:
        raise DefinitionError(f"monster '{mid}': health and move_interval must be >= 1")
    if m.missile not in (None, "hitscan", "projectile"):
        raise DefinitionError(f"monster '{mid}': missile must be 'hitscan' or 'projectile'")
    if m.missile and m.missile_damage is None and m.missile == "hitscan":
        raise DefinitionError(f"monster '{mid}': hitscan requires missile_damage")
    return m


def parse_pickup(pid: str, d: dict) -> PickupDef:
    r = _Reader(d, f"pickup '{pid}'")
    ptype = r.get("type", str)
    core = PickupDef(pid, ptype, r.get("sprite", str), r.get("message", str), r.get("sound", str, "pickup"),
                     r.get("count_item", bool, ptype in ("health", "armor", "key")), {})
    for key in ("type", "sprite", "message", "sound", "count_item"):
        r.used.add(key)
    params = {k: v for k, v in d.items() if k not in r.used and not k.startswith("_")}
    missing = BUILTIN_PICKUP_PARAMS.get(ptype, set()) - set(params)
    if missing:
        raise DefinitionError(f"pickup '{pid}': type '{ptype}' requires fields {sorted(missing)}")
    return PickupDef(pid, ptype, core.sprite, core.message, core.sound, core.count_item, params)


def parse_settings(d: dict) -> Settings:
    r = _Reader(d, "settings")
    ps = _Reader(r.get("player_start", dict), "settings.player_start")
    start = PlayerStart(ps.get("health", int), ps.get("armor", int, 0), tuple(ps.get("weapons", list)),
                        ps.get("ammo", dict, {}))
    ps.done()
    s = Settings(r.get("always_run", bool, True), r.get("mouse_sensitivity", float, 0.12),
                 r.get("start_map", str, "map01"), r.get("ammo_max", dict), start)
    r.done()
    return s


def parse_all(raw: dict[str, dict]) -> Definitions:
    """raw: {"weapons": {...}, "monsters": {...}, "projectiles": {...}, "pickups": {...}, "settings": {...}}."""
    defs = Definitions(
        weapons={k: parse_weapon(k, v) for k, v in raw.get("weapons", {}).items()},
        monsters={k: parse_monster(k, v) for k, v in raw.get("monsters", {}).items()},
        projectiles={k: parse_projectile(k, v) for k, v in raw.get("projectiles", {}).items()},
        pickups={k: parse_pickup(k, v) for k, v in raw.get("pickups", {}).items()},
        settings=parse_settings(raw.get("settings", {})))
    _cross_validate(defs)
    return defs


def _cross_validate(defs: Definitions) -> None:
    ammo = defs.settings.ammo_max
    for w in defs.weapons.values():
        if w.ammo and w.ammo not in ammo:
            raise DefinitionError(f"weapon '{w.id}': unknown ammo type '{w.ammo}' (add it to settings.ammo_max)")
        if w.projectile and w.projectile not in defs.projectiles:
            raise DefinitionError(f"weapon '{w.id}': unknown projectile '{w.projectile}'")
    for m in defs.monsters.values():
        if m.missile == "projectile" and m.missile_projectile not in defs.projectiles:
            raise DefinitionError(f"monster '{m.id}': unknown projectile '{m.missile_projectile}'")
        if m.drop and m.drop not in defs.pickups:
            raise DefinitionError(f"monster '{m.id}': unknown drop item '{m.drop}'")
    for p in defs.pickups.values():
        if p.type == "weapon" and p.params["weapon"] not in defs.weapons:
            raise DefinitionError(f"pickup '{p.id}': unknown weapon '{p.params['weapon']}'")
        if p.type == "ammo" and p.params["ammo"] not in ammo:
            raise DefinitionError(f"pickup '{p.id}': unknown ammo type '{p.params['ammo']}'")
    for wid in defs.settings.player_start.weapons:
        if wid not in defs.weapons:
            raise DefinitionError(f"settings.player_start: unknown weapon '{wid}'")
