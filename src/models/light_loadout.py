"""Light & Sky loadout: slots, what is equipped in them, and Light/Super Energy.

Owned powers live in the character's ``light_aspects``, ``light_abilities``,
``light_grenades`` and ``supers`` lists (what the creator and XP Shop write).
What is *equipped* is kept separately under ``light_loadout``:

    {"aspects": [name | None, ...],     # one entry per unlocked Aspect Slot
     "abilities": [name | None, ...],   # one entry per unlocked Ability Slot
     "super": name | None,              # a Character has a single Super at a time
     "seen": [name, ...]}               # owned powers already offered a slot

Energy is kept in ``light_energy`` and ``super_energy`` (0-100 by default).

This module has no Qt dependency so the rules can be tested on their own.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from src.models.xp_shop import XpShop

DEFAULT_MAX_ENERGY = 100
DEFAULT_ASPECT_MAXIMUM = 4
DEFAULT_ABILITY_EXTRA_SLOTS = 3
DEFAULT_ABILITY_SLOT_COST = 500


def _as_list(value) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value] if value else []


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _fold(text) -> str:
    return str(text or "").strip().casefold()


@dataclass
class Slot:
    """One tile on the Light page."""

    kind: str  # "aspect" | "ability" | "super"
    number: int  # 1-based
    unlocked: bool
    equipped: Optional[str] = None
    unlock_cost: int = 0  # XP to buy this slot (locked slots only)
    unlock_note: str = ""  # e.g. "Buy Aspect Slot 2 first"


@dataclass
class Power:
    """Display details for an owned aspect, ability, grenade or super."""

    name: str
    kind: str  # "Light Aspect" | "Light Ability" | "Light Grenade"
    connection: str = ""
    category: str = ""
    guardian_class: str = ""
    light_cost: Any = None  # int, "X", or None
    experience_cost: int = 0
    description: str = ""
    super_description: str = ""
    stats: list[str] = field(default_factory=list)  # grenade damage, range...

    def energy_cost(self, as_super: bool = False, multiplier: int = 2) -> Optional[int]:
        """Energy to use the power, or None when it varies ("X") or is unknown."""
        if isinstance(self.light_cost, bool) or not isinstance(self.light_cost, (int, float)):
            return None
        cost = int(self.light_cost)
        return cost * multiplier if as_super else cost

    def energy_text(self, as_super: bool = False, multiplier: int = 2) -> str:
        cost = self.energy_cost(as_super, multiplier)
        pool = "Super Energy" if as_super else "Light Energy"
        if cost is not None:
            return f"{cost} {pool}"
        if self.light_cost in (None, ""):
            return f"— {pool}"
        prefix = f"{multiplier} x " if as_super else ""
        return f"{prefix}{self.light_cost} {pool}"


class LightLoadout:
    """Light & Sky slot and energy rules for one character dict (edited in place)."""

    def __init__(self, character: dict[str, Any], game_data=None, ruleset: str = "Light & Sky"):
        self.character = character
        self.game_data = game_data
        self.shop = XpShop(character, game_data, ruleset)
        self._powers = self._index_powers()

    # -----------------------------------------------------------------
    # Rules documents
    # -----------------------------------------------------------------
    def _document(self, family, name):
        if self.game_data is None:
            return {}
        document = self.game_data.get(family, name)
        return document if isinstance(document, dict) else {}

    @property
    def ability_rules(self) -> dict:
        return self._document("light_ability_rules", "light_ability_rules").get(
            "light_abilities", {}
        )

    @property
    def aspect_rules(self) -> dict:
        return (
            self._document("light_aspect_rules", "light_aspect_rules")
            .get("light_aspects", {})
            .get("rules", {})
        )

    @property
    def energy_rules(self) -> dict:
        return self.ability_rules.get("energy", {})

    @property
    def super_energy_multiplier(self) -> int:
        return _int(self.ability_rules.get("supers", {}).get("energy_cost_multiplier"), 2)

    @property
    def grenade_super_rule(self) -> str:
        return self.ability_rules.get("grenade_supers", {}).get("rule", "")

    # -----------------------------------------------------------------
    # Owned powers
    # -----------------------------------------------------------------
    def owned_aspects(self) -> list[str]:
        return self._unique(self.character.get("light_aspects"))

    def owned_abilities(self) -> list[str]:
        """Light Abilities and Light Grenades: both fill Light Ability Slots."""
        return self._unique(
            _as_list(self.character.get("light_abilities"))
            + _as_list(self.character.get("light_grenades"))
        )

    def owned_supers(self) -> list[str]:
        return self._unique(self.character.get("supers"))

    @staticmethod
    def _unique(values) -> list[str]:
        seen, result = set(), []
        for value in _as_list(values):
            if isinstance(value, str) and value and _fold(value) not in seen:
                seen.add(_fold(value))
                result.append(value)
        return result

    def power(self, name) -> Power:
        """Details for a power by name; a bare Power when the data has no record."""
        return self._powers.get(_fold(name)) or Power(name=str(name), kind="")

    def _index_powers(self) -> dict[str, Power]:
        powers: dict[str, Power] = {}
        aspects = self._document("light_aspects", "light_aspects").get("light_aspects") or {}
        for connection, records in aspects.items():
            for record in records if isinstance(records, list) else []:
                if isinstance(record, dict) and record.get("name"):
                    powers[_fold(record["name"])] = Power(
                        name=record["name"],
                        kind="Light Aspect",
                        connection=str(connection).title(),
                        experience_cost=_int(record.get("experience_cost")),
                        description=record.get("description", ""),
                    )
        document = self._document("light_abilities", "light_abilities_and_grenades")
        for record in document.get("abilities", []):
            if isinstance(record, dict) and record.get("name"):
                powers[_fold(record["name"])] = self._ability_power(record)
        for record in document.get("grenades", []):
            if isinstance(record, dict) and record.get("name"):
                stats = []
                if record.get("damage_roll") or record.get("base_damage"):
                    damage = record.get("damage_roll", "")
                    if record.get("base_damage"):
                        damage = f"{damage}+{record['base_damage']}" if damage else record["base_damage"]
                    stats.append(f"Damage {damage}")
                if record.get("pierce") not in (None, ""):
                    stats.append(f"Pierce {record['pierce']}")
                if record.get("range"):
                    stats.append(str(record["range"]))
                description = record.get("special_rules", "")
                if record.get("second_detonation"):
                    description = f"{description} Second detonation: {record['second_detonation']}".strip()
                powers[_fold(record["name"])] = Power(
                    name=record["name"],
                    kind="Light Grenade",
                    connection=record.get("connection", ""),
                    category="Grenade",
                    light_cost=record.get("light_cost"),
                    experience_cost=_int(record.get("experience_cost")),
                    description=description,
                    super_description=self.grenade_super_rule,
                    stats=stats,
                )
        weapon = (
            self._document("light_weapon_abilities", "light_weapon_abilities")
            .get("light_weapon_abilities", {})
            .get("base_ability")
        )
        if isinstance(weapon, dict) and weapon.get("name"):
            powers.setdefault(
                _fold(weapon["name"]), self._ability_power(dict(weapon, category="Weapon"))
            )
        return powers

    @staticmethod
    def _ability_power(record) -> Power:
        return Power(
            name=record["name"],
            kind="Light Ability",
            connection=record.get("connection", ""),
            category=record.get("category", ""),
            guardian_class=record.get("class", "") or "",
            light_cost=record.get("light_cost"),
            experience_cost=_int(record.get("experience_cost")),
            description=record.get("description", ""),
            super_description=record.get("super_description", ""),
        )

    # -----------------------------------------------------------------
    # Slots
    # -----------------------------------------------------------------
    def aspect_slot_count(self) -> int:
        return self.shop.aspect_slots()

    def aspect_slot_maximum(self) -> int:
        """The rules' maximum plus free slots (e.g. Passive), which are not purchasable ones."""
        slots = self.aspect_rules.get("aspect_slots", {})
        maximum = _int(slots.get("maximum_slots"), DEFAULT_ASPECT_MAXIMUM)
        return max(self.aspect_slot_count(), maximum + self.shop.light_bonus("bonus_aspect_slots"))

    def ability_slot_count(self) -> int:
        return self.shop.ability_slots()

    def ability_slot_maximum(self) -> int:
        slots = self.ability_rules.get("rules", {}).get("ability_slots", {})
        extra = _int(slots.get("additional_slots"), DEFAULT_ABILITY_EXTRA_SLOTS)
        purchased = _int(self.character.get("light_ability_slots_purchased"))
        return self.ability_slot_count() + max(0, extra - purchased)

    def _aspect_slot_cost(self, number) -> int:
        """XP for locked Aspect Slot ``number``: the price of the purchase that unlocks it.

        Purchases are priced in order (200, 400, 800), so free slots such as
        Passive's shift which slot number each purchase opens.
        """
        costs = self.aspect_rules.get("aspect_slots", {}).get("additional_slot_costs", [])
        purchased = _int(self.character.get("light_aspect_slots_purchased"))
        index = purchased + (number - self.aspect_slot_count() - 1)
        return _int(costs[index].get("experience_cost")) if 0 <= index < len(costs) else 0

    def _ability_slot_cost(self) -> int:
        slots = self.ability_rules.get("rules", {}).get("ability_slots", {})
        return _int(slots.get("cost_per_additional_slot"), DEFAULT_ABILITY_SLOT_COST)

    def loadout(self) -> dict:
        """The saved loadout, cleaned up against owned powers and unlocked slots.

        Powers the character has not had before (bought since the last look, or
        every power on a save from before loadouts existed) drop into the first
        empty slot of their kind, so a purchase shows up ready to use. Powers
        the player took out of a slot stay out.
        """
        saved = self.character.get("light_loadout")
        saved = saved if isinstance(saved, dict) else {}
        seen = {_fold(name) for name in _as_list(saved.get("seen"))}
        aspects = self._fit(saved.get("aspects"), self.owned_aspects(), self.aspect_slot_count(), seen)
        abilities = self._fit(saved.get("abilities"), self.owned_abilities(), self.ability_slot_count(), seen)
        owned_supers = {_fold(name): name for name in self.owned_supers()}
        active_super = owned_supers.get(_fold(saved.get("super")))
        if active_super is None:
            new_supers = [name for name in self.owned_supers() if _fold(name) not in seen]
            active_super = new_supers[0] if new_supers else None
        owned = self.owned_aspects() + self.owned_abilities() + self.owned_supers()
        loadout = {
            "aspects": aspects,
            "abilities": abilities,
            "super": active_super,
            "seen": self._unique(owned),
        }
        self.character["light_loadout"] = loadout
        return loadout

    @staticmethod
    def _fit(saved, owned, count, seen) -> list:
        owned_by_fold = {_fold(name): name for name in owned}
        slots: list = [None] * count
        used = set()
        for index, name in enumerate(_as_list(saved)[:count] if isinstance(saved, list) else []):
            folded = _fold(name)
            if folded in owned_by_fold and folded not in used:
                slots[index] = owned_by_fold[folded]
                used.add(folded)
        for name in owned:
            folded = _fold(name)
            if folded in used or folded in seen or None not in slots:
                continue
            slots[slots.index(None)] = name
            used.add(folded)
        return slots

    def slots(self, kind: str) -> list[Slot]:
        """Every possible slot of a kind ("aspect", "ability", "super"), locked or not."""
        loadout = self.loadout()
        if kind == "super":
            return [Slot("super", 1, True, loadout["super"])]
        if kind == "aspect":
            equipped, unlocked, maximum = (
                loadout["aspects"], self.aspect_slot_count(), self.aspect_slot_maximum()
            )
        elif kind == "ability":
            equipped, unlocked, maximum = (
                loadout["abilities"], self.ability_slot_count(), self.ability_slot_maximum()
            )
        else:
            raise ValueError(f"Unknown slot kind: {kind}")
        result = []
        for number in range(1, maximum + 1):
            if number <= unlocked:
                result.append(Slot(kind, number, True, equipped[number - 1]))
                continue
            cost = self._aspect_slot_cost(number) if kind == "aspect" else self._ability_slot_cost()
            note = "" if number == unlocked + 1 else f"Unlock slot {unlocked + 1} first"
            result.append(Slot(kind, number, False, None, cost, note))
        return result

    def available_for(self, kind: str, number: int) -> list[str]:
        """Owned powers that can go in a slot: not already equipped elsewhere."""
        loadout = self.loadout()
        if kind == "super":
            return self.owned_supers()
        key = "aspects" if kind == "aspect" else "abilities"
        owned = self.owned_aspects() if kind == "aspect" else self.owned_abilities()
        elsewhere = {
            _fold(name)
            for index, name in enumerate(loadout[key])
            if name and index != number - 1
        }
        return [name for name in owned if _fold(name) not in elsewhere]

    def equip(self, kind: str, number: int, name: Optional[str]) -> None:
        """Put a power in a slot (None empties it). Moves it if equipped in another slot."""
        loadout = self.loadout()
        if kind == "super":
            owned = {_fold(value): value for value in self.owned_supers()}
            loadout["super"] = owned.get(_fold(name)) if name else None
            return
        key = "aspects" if kind == "aspect" else "abilities"
        slots = loadout[key]
        if not 1 <= number <= len(slots):
            raise ValueError(f"{kind.title()} Slot {number} is locked")
        if name:
            owned = self.owned_aspects() if kind == "aspect" else self.owned_abilities()
            owned_by_fold = {_fold(value): value for value in owned}
            if _fold(name) not in owned_by_fold:
                raise ValueError(f"{name} is not owned")
            name = owned_by_fold[_fold(name)]
            for index, value in enumerate(slots):
                if value and _fold(value) == _fold(name):
                    slots[index] = None
        slots[number - 1] = name or None

    def equipped_aspects(self) -> list[str]:
        return [name for name in self.loadout()["aspects"] if name]

    # -----------------------------------------------------------------
    # Energy
    # -----------------------------------------------------------------
    def maximum(self, pool: str) -> int:
        """Energy limit: 100 by the rules, plus Energize (+25 Light) / Super (+20 Super)."""
        key = "maximum_light_energy" if pool == "light" else "maximum_super_energy"
        bonus = "bonus_light_energy" if pool == "light" else "bonus_super_energy"
        return _int(self.energy_rules.get(key), DEFAULT_MAX_ENERGY) + self.shop.light_bonus(bonus)

    def energy(self, pool: str) -> int:
        key = self._energy_key(pool)
        value = self.character.get(key)
        maximum = self.maximum(pool)
        value = maximum if value is None else _int(value, maximum)
        value = min(maximum, max(0, value))
        self.character[key] = value
        return value

    def set_energy(self, pool: str, value: int) -> int:
        self.character[self._energy_key(pool)] = min(self.maximum(pool), max(0, _int(value)))
        return self.character[self._energy_key(pool)]

    def gain(self, light: int = 0, super_: int = 0) -> tuple[int, int]:
        return (
            self.set_energy("light", self.energy("light") + light),
            self.set_energy("super", self.energy("super") + super_),
        )

    def spend(self, pool: str, amount: int) -> bool:
        """Spend energy; False (and nothing spent) when there is not enough."""
        current = self.energy(pool)
        if amount > current:
            return False
        self.set_energy(pool, current - amount)
        return True

    @staticmethod
    def _energy_key(pool: str) -> str:
        if pool not in ("light", "super"):
            raise ValueError(f"Unknown energy pool: {pool}")
        return "light_energy" if pool == "light" else "super_energy"

    # Regeneration events from the Light Abilities energy rules: (label, light, super, rule)
    def regeneration_events(self) -> list[tuple[str, int, int, str]]:
        rules = self.energy_rules
        return [
            ("New Turn", 5, 5, rules.get("turn_regeneration", "")),
            ("Defeat (Weapons)", 5, 5, rules.get("normal_defeat_regeneration", "")),
            ("Defeat (Light Ability)", 0, 10, rules.get("light_ability_defeat_regeneration", "")),
            ("Assist Ally", 0, 5, rules.get("ally_support_regeneration", "")),
        ]
