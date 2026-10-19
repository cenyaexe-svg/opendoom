"""Pickup type handlers. A handler is (game, player, pickup_def) -> bool (whether the item was picked up).

Custom types are added via ModAPI.register_pickup_type or by writing directly into HANDLERS.
As in Doom, an item stays on the floor if the player does not need it (full health, full ammo).
"""
from __future__ import annotations


def _health(game, player, d) -> bool:
    cap = d.params["max"]
    if player.health >= cap:
        return False
    player.health = min(cap, player.health + d.params["amount"])
    return True


def _armor(game, player, d) -> bool:
    amount, cap, atype = d.params["amount"], d.params["max"], d.params["armor_type"]
    if amount >= cap:                        # full armor: replaces the current one if better
        if player.armor >= amount:
            return False
        player.armor, player.armor_type = amount, atype
        return True
    if player.armor >= cap:                  # bonus: adds
        return False
    player.armor = min(cap, player.armor + amount)
    player.armor_type = max(player.armor_type, atype)
    return True


def _ammo(game, player, d) -> bool:
    kind = d.params["ammo"]
    cap = game.defs.settings.ammo_max[kind]
    if player.ammo.get(kind, 0) >= cap:
        return False
    player.ammo[kind] = min(cap, player.ammo.get(kind, 0) + d.params["amount"])
    return True


def _weapon(game, player, d) -> bool:
    wid = d.params["weapon"]
    wdef = game.defs.weapons[wid]
    got = False
    if wid not in player.weapons:
        player.weapons.add(wid)
        player.pending = wid                 # as in Doom: a newly picked-up weapon is raised
        got = True
    if wdef.ammo:
        cap = game.defs.settings.ammo_max[wdef.ammo]
        if player.ammo.get(wdef.ammo, 0) < cap:
            player.ammo[wdef.ammo] = min(cap, player.ammo.get(wdef.ammo, 0) + d.params["ammo_amount"])
            got = True
    return got


def _key(game, player, d) -> bool:
    if d.params["key"] in player.keys:
        return False
    player.keys.add(d.params["key"])
    return True


HANDLERS = {"health": _health, "armor": _armor, "ammo": _ammo, "weapon": _weapon, "key": _key}


def try_pickup(game, player, pickup) -> bool:
    d = pickup.pdef
    handler = HANDLERS.get(d.type)
    if handler is None or not handler(game, player, d):
        return False
    pickup.removed = True
    player.bonus_count = 6
    if d.count_item:
        game.items += 1
    game.message(d.message)
    game.play_sound(d.sound, None, None)
    game.bus.emit("pickup", game=game, pickup_id=d.id)
    return True
