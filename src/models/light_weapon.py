"""Light Weapon builder rules (Light & Sky, Universal Weapon Ability).

The Light Weapon Light Ability forms a weapon of Light. The player picks:

* the Connection it is made of (its color, and which effects it can take),
* the weapon it is based on: any Melee Weapon or Physical Shield from the
  Standard Melee Weapons list (data/light_and_sky/equipment/melee_weapons.json)
  or any Emblem-system Ranged Weapon (data/light_and_sky/equipment/Weapons.json,
  one row of its roll table),
* up to 4 effects from the Universal list and the chosen Connection's list
  (every Light Connection's lists with Prismatic).

Costs, from the book:

* Light Cost = the weapon's cR cost rounded up to the nearest 5 (ranged weapons
  use their type's "base cost for Light Abilities").
* As a Light Ability it spends Light Cost per Turn; each effect adds double its
  listed Energy.
* As a Super it spends double Energy (all Supers do) from Super Energy, plus
  each effect's listed Energy.

The ability can be taken many times. Each build is stored on the character:

    character["light_weapons"] = [build, ...]

and its ``name`` (e.g. "Light Weapon: Solar Kukri") goes in ``light_abilities``
or ``supers`` like any other power, so slots and the Light page work unchanged.

No Qt here, so the rules can be tested on their own.
"""
from __future__ import annotations

import math
import random
import re
import uuid
from dataclasses import dataclass, field
from typing import Optional

from src.models.derived_stats import characteristic_modifier

BASE_NAME = "Light Weapon"
MAX_EFFECTS = 4
LIGHT_COST_STEP = 5
DEFAULT_SUPER_ENERGY_MULTIPLIER = 2
DEFAULT_SUPER_XP_MULTIPLIER = 1.5
DEFAULT_EXPERIENCE_COST = 500
# Effects priced "per duplicate" / "per bounce": the book caps duplicates at 5
# and gives no cap for bounces, so both use this upper bound.
MAX_EFFECT_COUNT = 5

MELEE = "Melee Weapon"
SHIELD = "Physical Shield"
RANGED = "Ranged Weapon"
CATEGORIES = (MELEE, SHIELD, RANGED)

MELEE_GROUP_LABELS = {
    "knives_daggers_swords": "Knives, Daggers, Swords",
    "axes_and_scythes": "Axes and Scythes",
    "hammers_and_clubs": "Hammers and Clubs",
    "chain_weapons": "Chain Weapons",
    "pole_weapons": "Pole Weapons",
    "fist_and_foot_weapons": "Fist and Foot Weapons",
    "physical_shields": "Physical Shields",
    "misc_weapons": "Misc Weapons",
}
ROLL_BANDS = [f"{low}-{low + 9}" for low in range(1, 100, 10)]
LIGHT_CONNECTIONS = ("Arc", "Solar", "Void")
DARKNESS_CONNECTIONS = ("Stasis", "Strand")
PRISMATIC = "Prismatic"


def _fold(text) -> str:
    return str(text or "").strip().casefold()


def _as_list(value) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value] if value else []


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _first_document(game_data, family: str) -> dict:
    if game_data is None:
        return {}
    for name in game_data.list(family):
        document = game_data.get(family, name)
        if isinstance(document, dict):
            return document
    return {}


def light_cost_for(cost_cr) -> int:
    """cR cost rounded up to the nearest 5 (33 -> 35, 40 -> 40)."""
    cost = max(0.0, float(cost_cr or 0))
    return int(math.ceil(cost / LIGHT_COST_STEP) * LIGHT_COST_STEP)


# ---------------------------------------------------------------------------
# Catalog records
# ---------------------------------------------------------------------------
@dataclass
class WeaponChoice:
    """A weapon a Light Weapon can be based on."""

    key: str  # "melee:Kukri" | "ranged:hand_cannons"
    name: str
    category: str  # MELEE | SHIELD | RANGED
    group: str  # "Knives, Daggers, Swords", "Hand Cannon", ...
    cost_cr: int
    record: dict = field(default_factory=dict)  # melee record, or the type's first row
    rows: list = field(default_factory=list)  # ranged roll-table rows (10)
    special_rules: list = field(default_factory=list)

    @property
    def light_cost(self) -> int:
        return light_cost_for(self.cost_cr)

    @property
    def is_ranged(self) -> bool:
        return self.category == RANGED

    def row(self, index: Optional[int]) -> dict:
        """Stats for a roll-table row (ranged) or the record itself (melee)."""
        if not self.rows:
            return dict(self.record)
        index = 0 if index is None else max(0, min(len(self.rows) - 1, int(index)))
        return dict(self.rows[index])


@dataclass
class Effect:
    key: str  # "universal:3"
    connection: str  # "Universal", "Solar", ...
    description: str
    energy: int  # listed additional Energy (per count for counted effects)
    per: str = ""  # "Per duplicate" etc.; empty for a flat cost

    @property
    def counted(self) -> bool:
        return bool(self.per)

    def label(self) -> str:
        unit = f" {self.per.lower()}" if self.per else ""
        return f"[+{self.energy}{unit}] {self.description}"


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
class LightWeaponRules:
    """The weapon list, effect lists and cost rules, read from GameData."""

    def __init__(self, game_data):
        self.game_data = game_data
        self._weapons: Optional[list[WeaponChoice]] = None

    # -- documents ----------------------------------------------------------
    @property
    def ability_document(self) -> dict:
        return _first_document(self.game_data, "light_weapon_abilities").get(
            "light_weapon_abilities", {}
        )

    @property
    def base_ability(self) -> dict:
        record = self.ability_document.get("base_ability")
        return record if isinstance(record, dict) else {}

    @property
    def super_rules(self) -> dict:
        document = _first_document(self.game_data, "light_ability_rules")
        return document.get("light_abilities", {}).get("supers", {})

    @property
    def super_energy_multiplier(self) -> int:
        return _int(self.super_rules.get("energy_cost_multiplier"), DEFAULT_SUPER_ENERGY_MULTIPLIER)

    def experience_cost(self, as_super: bool) -> int:
        base = _int(self.base_ability.get("experience_cost"), DEFAULT_EXPERIENCE_COST)
        if not as_super:
            return base
        multiplier = self.super_rules.get("experience_cost_multiplier", DEFAULT_SUPER_XP_MULTIPLIER)
        return int(base * float(multiplier))

    # -- weapons ------------------------------------------------------------
    def weapons(self, category: Optional[str] = None) -> list[WeaponChoice]:
        if self._weapons is None:
            self._weapons = self._melee_choices() + self._ranged_choices()
        if category is None:
            return list(self._weapons)
        return [weapon for weapon in self._weapons if weapon.category == category]

    def weapon(self, key: str) -> Optional[WeaponChoice]:
        return next((weapon for weapon in self.weapons() if weapon.key == key), None)

    def _melee_choices(self) -> list[WeaponChoice]:
        groups = _first_document(self.game_data, "lns_melee_weapons").get("lns_melee_weapons", {})
        choices = []
        for group_key, records in groups.items():
            category = SHIELD if group_key == "physical_shields" else MELEE
            label = MELEE_GROUP_LABELS.get(group_key, group_key.replace("_", " ").title())
            for record in records if isinstance(records, list) else []:
                if not isinstance(record, dict) or not record.get("name"):
                    continue
                choices.append(
                    WeaponChoice(
                        key=f"melee:{record['name']}",
                        name=record["name"],
                        category=category,
                        group=label,
                        cost_cr=_int(record.get("price")),
                        record=record,
                        special_rules=list(record.get("special_rules") or []),
                    )
                )
        return choices

    def _ranged_choices(self) -> list[WeaponChoice]:
        document = _first_document(self.game_data, "lns_weapons")
        choices = []
        for type_key, groups in document.items():
            if not isinstance(groups, list):
                continue
            rules, rows, cost = [], [], None
            for group in groups:
                if not isinstance(group, dict):
                    continue
                for rule_group in group.get("weapon_special_rules", []):
                    rules.extend(rule_group.get("special_rules", []))
                rows.extend(group.get("weapon_models", []))
                if "light_ability_base_cost_cr" in group:
                    cost = group["light_ability_base_cost_cr"]
            if not rows or cost is None:
                continue
            name = rows[0].get("weapon_type") or type_key.replace("_", " ").title()
            choices.append(
                WeaponChoice(
                    key=f"ranged:{type_key}",
                    name=name,
                    category=RANGED,
                    group=name,
                    cost_cr=_int(cost),
                    record=dict(rows[0]),
                    rows=[dict(row) for row in rows],
                    special_rules=rules,
                )
            )
        return choices

    @staticmethod
    def roll_band(index: int) -> str:
        return ROLL_BANDS[index] if 0 <= index < len(ROLL_BANDS) else str(index + 1)

    @staticmethod
    def roll_row(rng: Optional[random.Random] = None) -> tuple[int, int]:
        """Roll 1D100 for a ranged roll table: (roll, row index)."""
        roll = (rng or random).randint(1, 100)
        return roll, (roll - 1) // 10

    # -- connections and effects -------------------------------------------
    def connection_options(self, character: dict) -> list[str]:
        """Connections the weapon can be made of: the character's own (not Prismatic itself).

        With Prismatic, every Light and Darkness Connection is available.
        """
        owned = [name for name in _as_list(character.get("connections")) if isinstance(name, str)]
        prismatic = any(_fold(name) == _fold(PRISMATIC) for name in owned)
        options = [name for name in owned if _fold(name) != _fold(PRISMATIC)]
        if prismatic:
            for name in LIGHT_CONNECTIONS + DARKNESS_CONNECTIONS:
                if _fold(name) not in {_fold(option) for option in options}:
                    options.append(name)
        return options or list(LIGHT_CONNECTIONS)

    @staticmethod
    def has_prismatic(character: dict) -> bool:
        return any(_fold(name) == _fold(PRISMATIC) for name in _as_list(character.get("connections")))

    def all_effects(self) -> list[Effect]:
        effects = []
        for connection, records in (self.ability_document.get("effects") or {}).items():
            for index, record in enumerate(records if isinstance(records, list) else []):
                if not isinstance(record, dict):
                    continue
                effects.append(
                    Effect(
                        key=f"{_fold(connection)}:{index}",
                        connection=str(connection).title(),
                        description=str(record.get("description", "")),
                        energy=_int(record.get("additional_light_energy")),
                        per=str(record.get("cost_modifier") or ""),
                    )
                )
        return effects

    def effects_for(self, connection: str, character: Optional[dict] = None) -> list[Effect]:
        """Universal effects plus the Connection's (every available Connection's with Prismatic)."""
        allowed = {"universal", _fold(connection)}
        if character is not None and self.has_prismatic(character):
            allowed |= {_fold(name) for name in self.connection_options(character)}
        return [effect for effect in self.all_effects() if _fold(effect.connection) in allowed]

    def effect(self, key: str) -> Optional[Effect]:
        return next((effect for effect in self.all_effects() if effect.key == key), None)

    # -- costs --------------------------------------------------------------
    def effects_energy(self, effects: list[dict], as_super: bool) -> int:
        """Energy the chosen effects add per Turn: listed as a Super, doubled otherwise."""
        listed = sum(_int(effect.get("energy")) * max(1, _int(effect.get("count"), 1)) for effect in effects)
        return listed if as_super else listed * 2

    def energy_per_turn(self, light_cost: int, effects: list[dict], as_super: bool) -> int:
        base = light_cost * self.super_energy_multiplier if as_super else light_cost
        return base + self.effects_energy(effects, as_super)

    # -- building -----------------------------------------------------------
    def build(
        self,
        weapon: WeaponChoice,
        connection: str,
        as_super: bool,
        effects: Optional[list[tuple[str, int]]] = None,
        row_index: Optional[int] = None,
        character: Optional[dict] = None,
        name: str = "",
        build_id: str = "",
    ) -> dict:
        """A saved Light Weapon build. ``effects`` is [(effect key, count), ...]."""
        chosen = []
        for key, count in effects or []:
            effect = self.effect(key)
            if effect is None:
                raise ValueError(f"Unknown Light Weapon effect: {key}")
            chosen.append(
                {
                    "key": effect.key,
                    "connection": effect.connection,
                    "description": effect.description,
                    "energy": effect.energy,
                    "per": effect.per,
                    "count": max(1, min(MAX_EFFECT_COUNT, _int(count, 1))) if effect.counted else 1,
                }
            )
        problems = self.problems(weapon, connection, chosen, character)
        if problems:
            raise ValueError(" ".join(problems))
        row_index = (row_index or 0) if weapon.is_ranged else None
        stats = self.profile(weapon, as_super, row_index, character)
        build = {
            "id": build_id or uuid.uuid4().hex[:8],
            "name": name or self.default_name(weapon, connection, as_super),
            "as_super": bool(as_super),
            "connection": connection,
            "weapon": {
                "key": weapon.key,
                "name": weapon.name,
                "category": weapon.category,
                "group": weapon.group,
                "cost_cr": weapon.cost_cr,
                "roll": self.roll_band(row_index) if row_index is not None else None,
                "row_index": row_index,
            },
            "light_cost": weapon.light_cost,
            "effects": chosen,
            "energy_per_turn": self.energy_per_turn(weapon.light_cost, chosen, as_super),
            "experience_cost": self.experience_cost(as_super),
            "stats": stats,
        }
        return build

    def problems(self, weapon, connection, effects: list[dict], character=None) -> list[str]:
        problems = []
        if weapon is None:
            problems.append("Choose a weapon.")
        if not connection:
            problems.append("Choose a Connection.")
        if len(effects) > MAX_EFFECTS:
            problems.append(f"A Light Weapon can have at most {MAX_EFFECTS} effects.")
        allowed = {effect.key for effect in self.effects_for(connection, character)}
        for effect in effects:
            if effect["key"] not in allowed:
                problems.append(
                    f"'{effect['description']}' is from the {effect['connection']} list; "
                    f"this weapon is {connection} (only Prismatic can mix Connections)."
                )
        return problems

    @staticmethod
    def default_name(weapon: WeaponChoice, connection: str, as_super: bool = False) -> str:
        """'Light Weapon: Solar Kukri', or 'Light Weapon Super: Solar Kukri'."""
        prefix = f"{BASE_NAME} Super" if as_super else BASE_NAME
        return f"{prefix}: {connection} {weapon.name}".strip()

    # -- modified weapon profile -------------------------------------------
    def profile(
        self,
        weapon: WeaponChoice,
        as_super: bool,
        row_index: Optional[int] = None,
        character: Optional[dict] = None,
    ) -> dict:
        """The weapon's stats with the Light Weapon bonuses applied.

        Damage Dice +1D10 (+2D10 as a Super), Special Damage on 9-10, and Base
        Damage and Pierce + the Warfare Characteristic Modifier used to attack
        (Warfare Melee for melee weapons and shields, Warfare Range for ranged).
        """
        stats = weapon.row(row_index)
        melee = not weapon.is_ranged or _fold(stats.get("rate_of_fire")) == "melee attack"
        warfare = "WFM" if melee else "WFR"
        warfare_label = "Warfare Melee" if melee else "Warfare Range"
        characteristics = (character or {}).get("characteristics") or {}
        modifier = (
            characteristic_modifier(_int(characteristics.get(warfare)))
            if warfare in characteristics
            else None
        )
        extra_dice = 2 if as_super else 1
        rules = list(weapon.special_rules) + list(stats.get("special_rules") or [])
        rules.append("Special Damage on 9 or 10")
        if weapon.is_ranged:
            rules.append("No ammunition; dissipates if the magazine runs out")
        profile = {
            "weapon_type": stats.get("weapon_type") or weapon.group,
            "damage": add_damage_dice(stats.get("damage"), extra_dice),
            "bonus_damage": add_modifier(stats.get("bonus_damage"), modifier, warfare_label),
            "pierce": add_modifier(stats.get("pierce"), modifier, warfare_label),
            "warfare": warfare,
            "warfare_modifier": modifier,
            "tags": list(stats.get("tags") or []),
            "special_rules": _unique(rules),
        }
        for field_name in ("reach", "range", "rate_of_fire", "magazine", "reload"):
            if stats.get(field_name) not in (None, ""):
                profile[field_name] = stats[field_name]
        for field_name in ("shield_armor", "breakpoints", "max_attacks_per_half_action"):
            if field_name in stats:
                profile[field_name] = stats[field_name]
        return profile


def _unique(values) -> list:
    seen, result = set(), []
    for value in values:
        if _fold(value) not in seen:
            seen.add(_fold(value))
            result.append(value)
    return result


_DICE = re.compile(r"^\s*(\d+)\s*D\s*10\b(.*)$", re.IGNORECASE)


def add_damage_dice(damage, extra: int) -> str:
    """'3D10' + 1 -> '4D10'; dice other than D10 get the D10s added on ('1D5 +1D10')."""
    text = "" if damage in (None, "", 0) else str(damage)
    match = _DICE.match(text)
    if match:
        return f"{int(match.group(1)) + extra}D10{match.group(2)}"
    if not text:
        return f"{extra}D10"
    return f"{text} +{extra}D10"


_LEADING_NUMBER = re.compile(r"^\s*([+-]?\d+)(.*)$")


def add_modifier(value, modifier: Optional[int], label: str) -> str:
    """Add the Warfare modifier to a Base Damage or Pierce value.

    With a known modifier the number is added in ('4 +Full Strength Modifier'
    + 3 -> '7 +Full Strength Modifier'); without one the modifier is named.
    """
    text = "" if value is None else str(value).strip()
    if modifier is None:
        return f"{text} +{label} Modifier".strip() if text else f"{label} Modifier"
    match = _LEADING_NUMBER.match(text)
    if match:
        return f"{int(match.group(1)) + modifier}{match.group(2)}"
    if not text:
        return str(modifier)
    return f"{modifier} {text if text.startswith(('+', '-')) else '+' + text}"


# ---------------------------------------------------------------------------
# Builds on a character
# ---------------------------------------------------------------------------
def builds(character: dict) -> list[dict]:
    """The character's Light Weapon builds (saved under ``light_weapons``)."""
    return [build for build in _as_list(character.get("light_weapons")) if isinstance(build, dict)]


def find_build(character: dict, name: str) -> Optional[dict]:
    return next((build for build in builds(character) if _fold(build.get("name")) == _fold(name)), None)


def is_light_weapon_name(name: str) -> bool:
    """The base ability's own name (what the shop and creator list)."""
    return _fold(name) == _fold(BASE_NAME)


def unique_name(character: dict, name: str, taken_names=()) -> str:
    """``name``, or ``name (2)``, ``name (3)``... if another power already uses it."""
    taken = {
        _fold(value)
        for field_name in ("light_abilities", "light_grenades", "supers")
        for value in _as_list(character.get(field_name))
    }
    taken |= {_fold(build.get("name")) for build in builds(character)}
    taken |= {_fold(value) for value in taken_names}
    if _fold(name) not in taken:
        return name
    number = 2
    while _fold(f"{name} ({number})") in taken:
        number += 1
    return f"{name} ({number})"


def add_build(character: dict, build: dict) -> dict:
    """Save a build and list it with the character's Light Abilities or Supers."""
    build = dict(build)
    build["name"] = unique_name(character, build.get("name") or BASE_NAME)
    character.setdefault("light_weapons", []).append(build)
    field_name = "supers" if build.get("as_super") else "light_abilities"
    character.setdefault(field_name, []).append(build["name"])
    return build


def remove_build(character: dict, name: str) -> Optional[dict]:
    build = find_build(character, name)
    if build is None:
        return None
    character["light_weapons"] = [b for b in builds(character) if b is not build]
    for field_name in ("light_abilities", "supers"):
        values = _as_list(character.get(field_name))
        if any(_fold(value) == _fold(name) for value in values):
            character[field_name] = [value for value in values if _fold(value) != _fold(name)]
    return build


def summary_parts(build: dict) -> tuple[list[str], list[str]]:
    """(weapon and stat lines, effect lines) for tiles and tooltips."""
    weapon = build.get("weapon") or {}
    stats = build.get("stats") or {}
    head = weapon.get("name", "")
    if weapon.get("roll"):
        head += f" (roll {weapon['roll']})"
    stat_lines = [f"{head} | {weapon.get('category', '')} | Light Cost {build.get('light_cost')}"]
    stat_parts = [f"Damage {stats.get('damage', '')} +{stats.get('bonus_damage', '')}"]
    if stats.get("pierce") not in (None, ""):
        stat_parts.append(f"Pierce {stats['pierce']}")
    for field_name, label in (("reach", "Reach"), ("range", "Range"), ("rate_of_fire", "ROF")):
        if stats.get(field_name):
            stat_parts.append(f"{label} {stats[field_name]}")
    if stats.get("tags"):
        stat_parts.append(" ".join(f"[{tag}]" for tag in stats["tags"]))
    stat_lines.append(" | ".join(stat_parts))
    if stats.get("special_rules"):
        stat_lines.append("Rules: " + ", ".join(stats["special_rules"]))
    effect_lines = []
    for effect in build.get("effects") or []:
        count = f" x{effect['count']}" if effect.get("per") else ""
        effect_lines.append(f"Effect ({effect.get('connection')}){count}: {effect.get('description')}")
    return stat_lines, effect_lines


def summary_lines(build: dict) -> list[str]:
    stat_lines, effect_lines = summary_parts(build)
    return stat_lines + effect_lines
