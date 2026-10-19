# Changelog

Versions follow `MAJOR.MINOR.PATCH`. The current version is stored in `VERSION` (also shown by `python main.py --version`
and in the window title). Release archives are named `opendoom-vX.Y.Z.zip`.

## 0.2.0 — English translation
- All code comments, docstrings, error messages, log messages, in-game texts (pickup messages, HUD overlays,
  weapon/monster names), JSON definitions, the demo level and the example mod are now in English.
- README rewritten in English. Added `VERSION`, `CHANGELOG.md`, `--version`.
- No gameplay changes. 54 tests pass (headless core).

## 0.1.0 — first release (Russian)
- Headless game core: sector levels, Doom-style movement/physics at 35 Hz, hitscan and projectile weapons,
  monster state machine, doors/keys/lifts/secrets/exit, procedural textures, sprites, HUD and sounds.
- Panda3D layer (renderer, HUD view, application, sound) written but not run in the dev environment.
- Mod system (JSON definitions + optional scripts behind `--allow-scripts`), `example_mod`.
