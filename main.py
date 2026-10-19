"""OpenDoom — entry point.

    python main.py                       run the base game
    python main.py --mod example_mod     with a mod (may be repeated)
    python main.py --list-mods
    python main.py --map map01 --allow-scripts
"""
from __future__ import annotations

import argparse
import logging
import sys

from config import ASSETS_DIR, MODS_DIR, VERSION
from engine.events import EventBus
from modding.api import ModAPI
from modding.mod_loader import ModError, discover_mods, load_game_data, resolve_order, run_mod_scripts


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="OpenDoom — a classic shooter in the spirit of Doom (1993)")
    ap.add_argument("--mod", action="append", default=[], metavar="ID", help="enable a mod (repeatable)")
    ap.add_argument("--map", default=None, help="start map (default from settings.json)")
    ap.add_argument("--allow-scripts", action="store_true", help="allow running mod Python scripts (unsafe)")
    ap.add_argument("--list-mods", action="store_true")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--version", action="version", version=f"OpenDoom {VERSION}")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s: %(message)s")

    available = discover_mods(MODS_DIR)
    if args.list_mods:
        for m in available.values():
            print(f"{m.id}  {m.version}  priority={m.priority}  {m.name}" + ("  [has script]" if m.script else ""))
        return 0
    try:
        mods = resolve_order(args.mod, available)
        defs, resources = load_game_data(ASSETS_DIR, mods)
    except ModError as e:
        print(f"Mod loading error: {e}", file=sys.stderr)
        return 2
    bus = EventBus()
    scripted = [m for m in mods if m.script]
    if scripted and not args.allow_scripts:
        logging.warning("Mods %s contain scripts — they are NOT run without --allow-scripts", [m.id for m in scripted])
    elif scripted:
        run_mod_scripts(scripted, ModAPI(bus, defs))

    from engine.application import OpenDoomApp          # Panda3D is imported only on a real launch
    OpenDoomApp(defs, resources, bus, args.map or defs.settings.start_map).run()
    return 0


if __name__ == "__main__":
    sys.exit(main())
