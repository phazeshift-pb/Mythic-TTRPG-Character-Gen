"""Light & Sky random loot: weapons and armor sets.

Ported from the Destiny TTRPG Loot Generator. The rolls work the same way
(rarity odds, exotic chance and perk counts all come from loot_rules.py), but
the tables come from the Light & Sky equipment data the character manager
already loads (data/light_and_sky/equipment), and every roll is returned as a
plain, JSON-ready dict so it can be saved straight into a character file.

No Qt here, so the rolls can be unit tested.
"""

import random
from typing import Dict, List, Optional

from .loot_rules import (
    ARMOR_EXOTIC_CHANCE,
    WEAPON_EXOTIC_CHANCE,
    perk_count_for_rarity,
    roll_rarity,
)

# Display label, generator key and data table for every weapon type, in UI order.
WEAPON_TYPES = [
    ("Hand Cannon", "hand_cannon", "hand_cannons"),
    ("Scout Rifle", "scout", "scout_rifles"),
    ("Pulse Rifle", "pulse", "pulse_rifles"),
    ("Auto Rifle", "auto", "auto_rifles"),
    ("Sidearm", "sidearm", "sidearms"),
    ("SMG", "smg", "smgs"),
    ("Combat Bow", "bow", "combat_bows"),
    ("Fusion Rifle", "fusion", "fusion_rifles"),
    ("Shotgun", "shotgun", "shotguns"),
    ("Sniper Rifle", "sniper", "sniper_rifles"),
    ("Trace Rifle", "trace", "trace_rifles"),
    ("Breech Grenade Launcher", "breech_gl", "breech_grenade_launchers"),
    ("Rocket Launcher", "rocket", "rocket_launchers"),
    ("Missile Launcher", "missile", "missile_launchers"),
    ("Heavy Grenade Launcher", "heavy_gl", "heavy_grenade_launchers"),
    ("Linear Fusion Rifle", "linear_fusion", "linear_fusion_rifles"),
    ("Machine Gun", "machine_gun", "machine_guns"),
    ("Heavy Machine Gun", "heavy_machine_gun", "heavy_machine_guns"),
    ("Glaive", "glaive", "glaives"),
    ("Heavy Sword", "heavy_sword", "heavy_swords"),
]
AMMO_TYPES = ["Primary", "Special", "Heavy"]
ARMOR_MATERIALS = ["plasteel", "sapphire", "hadronic"]
ARMOR_SLOTS = ("head", "arms", "chest", "legs")


class LootDataMissing(ValueError):
    """The Light & Sky equipment data is not loaded."""


def _document(game_data, family: str) -> dict:
    names = game_data.list(family) if game_data is not None else []
    if not names:
        raise LootDataMissing(
            f"Light & Sky loot data ('{family}') is not loaded. "
            "Load the character with the Light & Sky ruleset."
        )
    return game_data.get(family, names[0])


def _perk(entry: dict) -> dict:
    return {
        "name": str(entry.get("name", "")),
        "description": str(entry.get("description", "")),
    }


def _number(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class LootGenerator:
    """Rolls Light & Sky weapons and armor sets from a loaded GameData."""

    def __init__(self, game_data, rng: Optional[random.Random] = None):
        self.rand = rng or random.Random()

        weapons_doc = _document(game_data, "lns_weapons")
        self.weapon_tables: Dict[str, List[dict]] = {}
        self.weapon_special_rules: Dict[str, List[str]] = {}
        for _, key, category in WEAPON_TYPES:
            groups = weapons_doc.get(category) or []
            rules, models = [], []
            for group in groups:
                for rule_group in group.get("weapon_special_rules", []):
                    rules.extend(rule_group.get("special_rules", []))
                models.extend(group.get("weapon_models", []))
            self.weapon_tables[key] = models
            self.weapon_special_rules[key] = rules

        weapon_perks = _document(game_data, "lns_weapon_perks")
        self.weapon_perks = [_perk(p) for p in weapon_perks.get("perks", [])]
        self.exotic_weapon_perks = [_perk(p) for p in weapon_perks.get("exotic_perks", [])]
        self.elements = [
            str(e.get("name", "")).title()
            for e in _document(game_data, "lns_elements").get("elements", [])
        ]

        armor_doc = _document(game_data, "lns_armor")
        self.armor_tables = {
            material: armor_doc.get(f"{material}_armor_table", [])
            for material in ARMOR_MATERIALS
        }
        self.armor_subtypes = armor_doc.get("armor_subtype", [])
        self.armor_variants = armor_doc.get("armor_variant", [])
        armor_perks = _document(game_data, "lns_armor_perks")
        self.armor_perks = [_perk(p) for p in armor_perks.get("armor_perks", [])]
        self.exotic_armor_perks = [
            _perk(p) for p in armor_perks.get("exotic_armor_perks", [])
        ]

    # -------------------------
    # Shared rarity / perk roll
    # -------------------------
    def _roll_rarity_and_perks(self, forced_rarity, exotic_chance, perks, exotics):
        rarity = forced_rarity or roll_rarity(self.rand)
        exotic = None
        # Same as the standalone generator: a forced non-Exotic rarity can
        # still be upgraded by the exotic chance.
        if forced_rarity == "Exotic" or self.rand.random() < exotic_chance:
            exotic = dict(self.rand.choice(exotics))
            rarity = "Exotic"
        count = min(perk_count_for_rarity(rarity, self.rand), len(perks))
        chosen = [dict(p) for p in self.rand.sample(perks, count)]
        return rarity, chosen, exotic

    # -------------------------
    # Weapons
    # -------------------------
    def weapon_types(self, ammo_type: Optional[str] = None):
        """(label, key) for every weapon type that has a model for this ammo."""
        return [
            (label, key)
            for label, key, _ in WEAPON_TYPES
            if self._weapon_candidates(key, ammo_type)
        ]

    def _weapon_candidates(self, weapon_type: str, ammo_type: Optional[str]):
        keys = [k for _, k, _ in WEAPON_TYPES] if weapon_type == "any" else [weapon_type]
        wanted = ammo_type.casefold() if ammo_type else None
        return [
            (key, model)
            for key in keys
            for model in self.weapon_tables.get(key, [])
            if wanted is None or str(model.get("ammo_type") or "").casefold() == wanted
        ]

    def generate_weapon(
        self,
        weapon_type: str = "any",
        forced_rarity: Optional[str] = None,
        ammo_type: Optional[str] = None,
        exotic_chance: float = WEAPON_EXOTIC_CHANCE,
    ) -> dict:
        candidates = self._weapon_candidates(weapon_type, ammo_type)
        if not candidates:
            filters = [f"weapon type '{weapon_type}'"]
            if ammo_type:
                filters.append(f"ammo type '{ammo_type}'")
            raise ValueError(f"No weapons found for {' and '.join(filters)}.")

        key, model = self.rand.choice(candidates)
        rarity, perks, exotic = self._roll_rarity_and_perks(
            forced_rarity, exotic_chance, self.weapon_perks, self.exotic_weapon_perks
        )
        return {
            "kind": "weapon",
            "weapon_type": model.get("weapon_type", ""),
            "rarity": rarity,
            "element": self.rand.choice(self.elements) if self.elements else "",
            "rate_of_fire": model.get("rate_of_fire"),
            "damage": model.get("damage"),
            "bonus_damage": model.get("bonus_damage"),
            "pierce": model.get("pierce"),
            "range": model.get("range"),
            "magazine": model.get("magazine"),
            "reload": model.get("reload"),
            "tags": list(model.get("tags", [])),
            "ammo_type": model.get("ammo_type"),
            "special_rules": list(self.weapon_special_rules.get(key, [])),
            "perks": perks,
            "exotic_perk": exotic,
        }

    # -------------------------
    # Armor
    # -------------------------
    @staticmethod
    def apply_armor_modifiers(base: dict, subtype: dict, variant: dict) -> dict:
        weight_modifier = _number(variant.get("weight_modifier"))
        armor_modifier = int(_number(variant.get("armor_modifier")))
        agility = int(
            (subtype.get("armor_variant_modifiers") or {}).get("agility", 0)
            + (variant.get("additional_modifiers") or {}).get("agility", 0)
        )
        ratings = base.get("armor", {})
        return {
            "weight": f"{_number(base.get('weight_kg')) + weight_modifier:.1f}",
            "armor_values": {
                slot: int(_number(ratings.get(slot))) + armor_modifier
                for slot in ARMOR_SLOTS
            },
            "agility_modifier": agility,
        }

    def _weighted(self, items, favored):
        weights = [5 if item.get("name") == favored else 2 for item in items]
        return self.rand.choices(items, weights=weights, k=1)[0]

    def generate_armor(
        self,
        material: Optional[str] = None,
        forced_rarity: Optional[str] = None,
        exotic_chance: float = ARMOR_EXOTIC_CHANCE,
    ) -> dict:
        material = (material or self.rand.choice(ARMOR_MATERIALS)).lower().strip()
        if material not in ARMOR_MATERIALS:
            raise ValueError(f"Invalid armor material: {material}")
        table = self.armor_tables.get(material) or []
        if not table:
            raise ValueError(f"No armor found for material '{material}'.")

        base = self.rand.choice(table)
        rarity, perks, exotic = self._roll_rarity_and_perks(
            forced_rarity, exotic_chance, self.armor_perks, self.exotic_armor_perks
        )
        subtype = self._weighted(self.armor_subtypes, "Standard Plating")
        variant = self._weighted(self.armor_variants, "Standard")
        modified = self.apply_armor_modifiers(base, subtype, variant)
        return {
            "kind": "armor",
            "material": material.title(),
            "rarity": rarity,
            "weight": modified["weight"],
            "armor_values": modified["armor_values"],
            "agility_modifier": modified["agility_modifier"],
            "subtype": subtype.get("name", ""),
            "variant": variant.get("name", ""),
            "perks": perks,
            "exotic_perk": exotic,
        }
