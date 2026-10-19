"""Global constants. Units and values come from original Doom (per-tic calculations)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = (ROOT / "VERSION").read_text(encoding="utf-8").strip() if (ROOT / "VERSION").exists() else "0.0.0"
ASSETS_DIR = ROOT / "assets"
MODS_DIR = ROOT / "mods"
CACHE_DIR = ROOT / ".cache"          # procedural sounds are generated here

TICRATE = 35                         # game logic runs at 35 Hz, as in Doom
TIC_DT = 1.0 / TICRATE

PLAYER_RADIUS = 16.0
PLAYER_HEIGHT = 56.0
PLAYER_EYE = 41.0
STEP_HEIGHT = 24.0                   # maximum step height
USE_RANGE = 64.0
MELEE_RANGE = 64.0
DEFAULT_RANGE = 2048.0               # hitscan range

# Player movement: thrust = command/32 units/tic², friction 0.90625 — this gives Doom its "slippery" feel.
FRICTION = 0.90625
STOP_SPEED = 0.0625
MAX_MOMENTUM = 30.0
THRUST_DIV = 32.0
RUN_FORWARD, WALK_FORWARD = 50.0, 25.0
RUN_SIDE, WALK_SIDE = 40.0, 24.0
KEY_TURN_DEG = 4.5                   # keyboard turn rate, degrees per tic
GRAVITY = 1.0

WEAPON_TOP = 32.0                    # weapon sprite position (as in Doom)
WEAPON_BOTTOM = 128.0
WEAPON_SWITCH_SPEED = 6.0
