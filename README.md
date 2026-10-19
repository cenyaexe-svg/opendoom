# OpenDoom v0.2.0

A modular Python + Panda3D shooter that recreates classic Doom (1993) mechanics: sector-based levels, Doom-style
thrust/friction movement at 35 Hz, hitscan with spread, monster state machines, doors/keys/lifts/secrets, a status bar
with a face, and mods that need no engine changes. All assets (textures, sprites, sounds) are procedural and original;
no assets from the original Doom are used. See `CHANGELOG.md` for version history.

## Run

    pip install -r requirements.txt
    python main.py                    # base game
    python main.py --mod example_mod  # demo mod (plasma pistol)
    python main.py --version
    python tests/run_plain.py         # tests without pytest; or simply: pytest

Controls: **W/S** forward/back, **A/D** strafe, **mouse / ←→** turn, **LMB / Ctrl** fire, **E / Space** use,
**1–7** select weapon, **Shift** inverts run (running is on by default), **Esc** pause, **F12** quit.

## What is implemented

- Doom-style movement: thrust `cmd/32`, friction 0.90625 (run ≈16.7 units/tic), strafe+run add up (≈21 units/tic
  diagonally), steps ≤24, gravity, wall sliding, lifts carry the player.
- Weapons: fist, pistol, shotgun (7 pellets), chaingun; cycle time in tics, accurate first shot, vertical auto-aim,
  weapon switching, auto-switch when out of ammo, raise/lower animation and bobbing.
- Monsters (zombieman, imp): idle → chase → attack/pain → dead; woken by sight (180° cone) or by gunfire noise through
  open sectors; missile chance as in `P_CheckMissileRange`; fireballs, melee, door opening, no walking off ledges, item drops.
- Doors (manual, keyed), lifts (walk triggers), exit, secrets, nukage (damage every 32 tics), armor (absorbs 1/3 or 1/2).
- HUD: AMMO / HEALTH / ARMS / face / ARMOR / keys / ammo reserves, red/gold screen flashes.
- One demo level: `assets/maps/map01.json`.

## Known limitations (honest)

- **The Panda3D layer (`rendering/renderer.py`, `ui/hud_view.py`, `engine/application.py`, `audio/sound_manager.py`)
  is written but has not been run in the development environment** (Panda3D was unavailable there). All logic, physics,
  mods and procedural assets are covered by tests (54) and soak-tested headlessly; please verify the graphical part
  yourself. If something renders wrongly (e.g. texture orientation), fixes are local: `TextureLibrary` and `meshgen.py`.
- Single-angle monster sprites (no 8 rotations), no music, main menu, saves, difficulty levels or teleports.
- Holes inside a sector are not rendered correctly; make pillars separate sectors at an edge or a notch
  (example: the nukage pool in the hall of the demo map).
- Rendering is full Panda3D 3D built from sector geometry, not Doom's software BSP renderer; the look comes from
  nearest filtering, fog and sector brightness.

## Layout

    engine/     events.py (event bus), resource_manager.py, application.py (Panda3D)
    world/      map_data, builder (polygons → lines), level_loader, collision, geometry
    gameplay/   game (35 Hz tic), player, combat, pickups, sectors (doors/lifts), triggers
    entities/   base, monsters, projectiles
    rendering/  canvas, textures, sprites (procedural), meshgen, renderer (Panda3D)
    ui/         hud (draws the bar into a Canvas), hud_view (Panda3D)
    audio/      synth (procedural WAV), sound_manager
    modding/    definitions (JSON validation), mod_loader, api
    assets/     defs/*.json, maps/*.json     mods/example_mod/     tests/

The core (`world`, `gameplay`, `entities`, `modding`) never imports Panda3D and is tested on its own.

## Mods

A mod is a directory `mods/<id>/` with a `mod.json` manifest:

    {"id": "my_mod", "name": "My Mod", "version": "1.0", "priority": 100, "depends": [], "script": null}

Contents (all optional): `defs/{weapons,monsters,projectiles,pickups,settings}.json`, `maps/*.json`, `sprites/*.png`,
`sounds/*.wav`, `textures/*.png`, `script.py`. Enable with `python main.py --mod my_mod`.

**Data merging.** A mod file is layered over the base by `id`. For an existing `id`, write only the fields to change
(`{"imp": {"health": 90}}`); for a new one, all required fields. `{"id": {"_remove": true}}` deletes an entry.
Dictionaries merge recursively, lists are replaced. Mods load by dependencies, then by ascending `priority`
(higher loads later and wins). Unknown fields and wrong types raise an error that names the exact location.

**Weapons** (`weapons.json`): `name, slot, ammo (type|null), ammo_per_shot, cycle_tics, damage [multiplier, die], pellets,
spread_deg, accurate_first_shot, range, melee, projectile (projectile id|null), sprite, tint [r,g,b], flash_tics, sound, noisy`.
Damage `[5,3]` = 5×(1..3), as in Doom. **Monsters**: `health, speed, move_interval, radius, height, pain_chance (of 256),
pain_tics, death_tics, melee_damage, missile ("hitscan"|"projectile"), missile_damage, missile_projectile, windup_tics,
recovery_tics, *_sound, drop, sprite`. A monster steps `speed` units every `move_interval` tics.
**Projectiles**: `sprite, explosion_sprite, speed, radius, damage, sound_launch, sound_hit, tint`. **Pickups**: `type`
(`health|armor|ammo|weapon|key` or your own), `sprite, message, sound, count_item` plus type parameters
(`amount, max, armor_type, ammo, weapon, ammo_amount, key`). **Settings**: `always_run, mouse_sensitivity, start_map,
ammo_max {type: max}, player_start {health, armor, weapons, ammo}`.

Sprites: monster `<sprite>_A..F` (idle, walk, walk, attack, pain, corpse); held weapon `<sprite>:ready` and `<sprite>:fire`
(as PNG files: `<sprite>_ready.png`). Example: `mods/example_mod` — a projectile weapon, stat changes and a new ammo type.

### Levels

Polygon format (easy to edit by hand): sectors with `polygon`, `floor, ceiling, light, floor_tex, ceil_tex, wall, tag,
damage, secret`; shared edges automatically become two-sided lines (T-junctions are inserted for you).
`line_props` sets special properties of a line by its endpoints:
`{"from": [x,y], "to": [x,y], "special": {...}, "textures": {"<sector id>": "tex"}}`.
Special lines: `{"action": "door"|"lift"|"exit", "trigger": "use"|"walk", "key": "red|blue|yellow", "tag": N, "repeat": true}`.
A door without `tag` opens the sector on the opposite side of the line from the player (closed door: ceiling = floor);
a lift needs a sector `tag`. Things: `{"type": "player_start"|monster id|pickup id, "x", "y", "angle"}`.
The explicit `vertices/linedefs` format is also accepted (`front` side is to the right of v1→v2). The next map is set by
`"next"`. A mod map with the same name replaces the base one.

### Python API (script.py)

    def register(api):
        api.on("monster_killed", lambda game, monster: api.message("Another one down!"))
        api.register_pickup_type("poison", lambda game, player, pickup_def: ...)   # True = item picked up

Events: `sound, message, tick, level_start, weapon_fired, monster_killed, pickup, player_damaged, level_exit`
(arguments are in `engine/events.py`). **Scripts run only with `--allow-scripts`** — they are arbitrary code;
JSON mod data never executes anything.
