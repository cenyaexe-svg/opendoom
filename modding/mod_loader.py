"""Mod discovery and loading.

Mod layout (a directory in mods/):
    mod.json               manifest: id, name, version, priority, depends, [script]
    defs/*.json            weapons / monsters / projectiles / pickups / settings (overrides and new entries)
    maps/*.json            levels (same-named ones replace the base maps)
    sprites|sounds|textures/  custom resources (PNG / WAV)
    script.py              (optional) Python code; executed ONLY with the --allow-scripts flag

Merging: data from defs/ is layered over the base data by id. For an existing id, specify
only the fields to change; for a new id, all of them. {"_remove": true} deletes the entry. A higher priority loads later.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from engine.resource_manager import ResourceManager
from modding.definitions import Definitions, DefinitionError, parse_all

log = logging.getLogger("opendoom")
CATEGORIES = ("weapons", "monsters", "projectiles", "pickups", "settings")


class ModError(Exception):
    pass


@dataclass
class ModManifest:
    id: str
    name: str
    version: str
    priority: int
    depends: list[str]
    script: str | None
    path: Path


def read_manifest(path: Path) -> ModManifest:
    try:
        d = json.loads((path / "mod.json").read_text(encoding="utf-8"))
        return ModManifest(d["id"], d.get("name", d["id"]), str(d.get("version", "0")), int(d.get("priority", 100)),
                           list(d.get("depends", [])), d.get("script"), path)
    except (OSError, KeyError, ValueError) as e:
        raise ModError(f"Invalid manifest in {path}: {e}") from e


def discover_mods(mods_dir: Path) -> dict[str, ModManifest]:
    found = {}
    if mods_dir.is_dir():
        for sub in sorted(mods_dir.iterdir()):
            if (sub / "mod.json").is_file():
                m = read_manifest(sub)
                found[m.id] = m
    return found


def resolve_order(selected: list[str], available: dict[str, ModManifest]) -> list[ModManifest]:
    """Load order: dependencies before dependents, otherwise by ascending priority."""
    order: list[ModManifest] = []
    visiting: set[str] = set()

    def visit(mod_id: str) -> None:
        if mod_id not in available:
            raise ModError(f"Mod or dependency '{mod_id}' not found")
        if mod_id in visiting:
            raise ModError(f"Circular mod dependency at '{mod_id}'")
        if any(m.id == mod_id for m in order):
            return
        visiting.add(mod_id)
        for dep in available[mod_id].depends:
            visit(dep)
        visiting.discard(mod_id)
        order.append(available[mod_id])

    for mid in sorted(selected, key=lambda i: (available[i].priority if i in available else 0, i)):
        visit(mid)
    return order


def _deep_merge(base: dict, patch: dict) -> dict:
    for k, v in patch.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_merge(base[k], v)
        else:
            base[k] = copy.deepcopy(v)
    return base


def _merge_category(base: dict, patch: dict, category: str) -> None:
    if category == "settings":
        _deep_merge(base, patch)
        return
    for ident, val in patch.items():
        if isinstance(val, dict) and val.get("_remove"):
            base.pop(ident, None)
        elif ident in base:
            _deep_merge(base[ident], val)
        else:
            base[ident] = copy.deepcopy(val)


def _read_defs(root: Path) -> dict[str, dict]:
    raw: dict[str, dict] = {}
    for cat in CATEGORIES:
        p = root / "defs" / f"{cat}.json"
        if p.is_file():
            try:
                raw[cat] = json.loads(p.read_text(encoding="utf-8"))
            except ValueError as e:
                raise ModError(f"{p}: invalid JSON: {e}") from e
    return raw


def load_game_data(assets_dir: Path, mods: list[ModManifest]) -> tuple[Definitions, ResourceManager]:
    raw = {c: {} for c in CATEGORIES}
    for c, data in _read_defs(assets_dir).items():
        _merge_category(raw[c], data, c)
    for mod in mods:
        for c, data in _read_defs(mod.path).items():
            _merge_category(raw[c], data, c)
        log.info("Loaded mod %s %s", mod.name, mod.version)
    try:
        defs = parse_all(raw)
    except DefinitionError as e:
        raise ModError(f"Error in definitions: {e}") from e
    roots = [m.path for m in reversed(mods)] + [assets_dir]
    return defs, ResourceManager(roots)


def run_mod_scripts(mods: list[ModManifest], api) -> None:
    """Runs mod script.py files. Call only if the player explicitly allowed it (--allow-scripts)."""
    for mod in mods:
        if not mod.script:
            continue
        path = mod.path / mod.script
        spec = importlib.util.spec_from_file_location(f"opendoom_mod_{mod.id}", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        if not hasattr(module, "register"):
            raise ModError(f"{path}: no register(api) function")
        module.register(api)
        log.info("Ran mod script %s", mod.id)
