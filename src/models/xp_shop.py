"""XP Shop: everything a finished character can spend Experience on.

Pure rules, no Qt. The shop works on a plain character dict (the
``character`` object of an exported character file) so the character sheet,
tests and tools can all share it.

Core purchases (data/xp_shop.json "xp_shop") are available to every ruleset.
Light & Sky purchases ("light_and_sky_xp_shop" plus the light power data in
data/light_and_sky) are only offered when the ruleset is "Light & Sky".
"""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Optional

from .character import CHAR_CODES, CHARACTERISTIC_NAME_TO_CODE
from .derived_stats import characteristic_modifier, max_wounds, mythic_value
from . import outliers as outlier_rules

LIGHT_AND_SKY = "Light & Sky"

# Tabs, in display order. Light & Sky tabs are dropped for Core characters.
CORE_CATEGORIES = (
    "Characteristics",
    "Skills",
    "Abilities",
    "Educations",
    "Training & Languages",
    "Luck & Wounds",
    "Soldier Type",
)
LIGHT_AND_SKY_CATEGORIES = (
    "Connections",
    "Light Slots",
    "Light Aspects",
    "Light Abilities",
    "Supers",
)

CHARACTERISTIC_NAMES = {code: name.title() for name, code in CHARACTERISTIC_NAME_TO_CODE.items()}
CHARACTERISTIC_NAMES["WFR"] = "Warfare Range"
CHARACTERISTIC_NAMES["WFM"] = "Warfare Melee"


class PurchaseError(ValueError):
    """Raised when an item can't be bought."""


@dataclass
class ShopItem:
    key: str
    category: str
    name: str
    cost: int
    current: str = ""
    next: str = ""
    description: str = ""
    source: str = "Core"
    # A hard block (maximum reached, missing requirement). GM override can't skip it.
    blocked: str = ""
    # A requirement the GM must sign off on. Buyable with GM override on.
    needs_gm: str = ""
    # Prerequisite text shown to the player.
    requirement: str = ""
    # Purchase choices. "text": the player types a value (suggestions list);
    # "options": [{"label", "cost", "value"}].
    prompt: Optional[str] = None
    prompt_label: str = ""
    suggestions: list[str] = field(default_factory=list)
    options: list[dict[str, Any]] = field(default_factory=list)
    kind: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


def _as_list(value) -> list:
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value] if value else []


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


# Light & Sky bonuses that soldier types (``special_rules``) and outliers
# (outlier records) can carry. Free slots never count against purchasable ones.
LIGHT_BONUS_KEYS = (
    "bonus_aspect_slots",
    "bonus_light_ability_slots",
    "bonus_light_energy",
    "bonus_super_energy",
)


def bonus_light_ability_slots(soldier_record) -> int:
    """Extra Light Ability Slots a soldier type gives (the Warlock's Power trait).

    Read from ``special_rules.bonus_light_ability_slots``.
    """
    return soldier_light_bonus(soldier_record, "bonus_light_ability_slots")


def soldier_light_bonus(soldier_record, key: str) -> int:
    if not isinstance(soldier_record, dict):
        return 0
    special = soldier_record.get("special_rules")
    return max(0, _int(special.get(key))) if isinstance(special, dict) else 0


def outlier_light_bonus(game_data, outlier_names, key: str) -> int:
    """Sum of ``key`` over the character's outliers (an outlier taken twice counts twice)."""
    if game_data is None:
        return 0
    records = {}
    for document in game_data.families.get("outliers", {}).values():
        outliers = document.get("outliers", {}) if isinstance(document, dict) else {}
        for record in outliers.get("list", []) if isinstance(outliers, dict) else []:
            if isinstance(record, dict) and record.get("name"):
                records.setdefault(_fold(record["name"]), record)
    return sum(
        max(0, _int(records.get(_fold(name), {}).get(key)))
        for name in _as_list(outlier_names)
    )


def starting_light_ability_slots(game_data, soldier_record, outlier_names=()) -> int:
    """Light Ability Slots a new character has: starting slots + class and outlier bonuses."""
    rules = {}
    if game_data is not None:
        document = game_data.get("light_ability_rules", "light_ability_rules") or {}
        rules = document.get("light_abilities", {}).get("rules", {}).get("ability_slots", {})
    return (
        _int(rules.get("starting_slots"), 2)
        + bonus_light_ability_slots(soldier_record)
        + outlier_light_bonus(game_data, outlier_names, "bonus_light_ability_slots")
    )


def starting_aspect_slots(game_data, soldier_record=None, outlier_names=()) -> int:
    """Aspect Slots a new character has: starting slots + class and outlier bonuses (Passive)."""
    rules = {}
    if game_data is not None:
        document = game_data.get("light_aspect_rules", "light_aspect_rules") or {}
        rules = document.get("light_aspects", {}).get("rules", {}).get("aspect_slots", {})
    return (
        _int(rules.get("starting_slots"), 1)
        + soldier_light_bonus(soldier_record, "bonus_aspect_slots")
        + outlier_light_bonus(game_data, outlier_names, "bonus_aspect_slots")
    )


def _fold(text) -> str:
    return str(text or "").strip().casefold()


class XpShop:
    def __init__(self, character: dict[str, Any], game_data, ruleset: str = ""):
        self.character = character
        self.game_data = game_data
        self.ruleset = ruleset or ""
        self.is_light_and_sky = self.ruleset == LIGHT_AND_SKY
        document = self._document("xp_shop", "xp_shop") or {}
        self.rules = document.get("xp_shop", {})
        self.lns_rules = document.get("light_and_sky_xp_shop", {})
        self.soldier_key, self.soldier = self._soldier_record()

    # ---------------------------------------------------------
    # Data helpers
    # ---------------------------------------------------------
    def _document(self, family, name):
        if self.game_data is None:
            return None
        return self.game_data.get(family, name)

    def _soldier_record(self):
        soldier_type = self.character.get("soldier_type")
        if self.game_data is None or not isinstance(soldier_type, str):
            return None, None
        for key, record in self.game_data.families.get("soldier_type", {}).items():
            if isinstance(record, dict) and record.get("name") == soldier_type:
                return key, record
        return None, None

    @property
    def available_xp(self) -> int:
        return max(0, _int(self.character.get("experience")))

    @property
    def earned_xp(self) -> Optional[int]:
        """Experience earned since character creation, if known."""
        creation = self.character.get("creation_experience")
        if creation is None:
            return None
        return max(0, _int(self.character.get("starting_experience")) - _int(creation))

    def categories(self) -> list[str]:
        categories = [
            category
            for category in CORE_CATEGORIES
            if category != "Soldier Type" or self._soldier_type_items()
        ]
        if self.is_light_and_sky:
            categories.extend(LIGHT_AND_SKY_CATEGORIES)
        return categories

    def items(self, category: str) -> list[ShopItem]:
        builders = {
            "Characteristics": self._characteristic_items,
            "Skills": self._skill_items,
            "Abilities": self._ability_items,
            "Educations": self._education_items,
            "Training & Languages": self._training_items,
            "Luck & Wounds": self._luck_and_wound_items,
            "Soldier Type": self._soldier_type_items,
        }
        if self.is_light_and_sky:
            builders.update(
                {
                    "Connections": self._connection_items,
                    "Light Slots": self._light_slot_items,
                    "Light Aspects": self._light_aspect_items,
                    "Light Abilities": self._light_ability_items,
                    "Supers": self._super_items,
                }
            )
        builder = builders.get(category)
        return builder() if builder else []

    def all_items(self) -> list[ShopItem]:
        return [item for category in self.categories() for item in self.items(category)]

    # ---------------------------------------------------------
    # Characteristics
    # ---------------------------------------------------------
    def free_advancements(self, code: str) -> int:
        """Advancement tiers the Soldier Type unlocked at Character Creation."""
        record = (self.soldier or {}).get("advancements") or {}
        text = record.get(code)
        if not isinstance(text, str):
            return 0
        tiers = self.rules.get("characteristic_advancements", {}).get("tiers", [])
        for tier in tiers:
            if _fold(tier["name"]) in _fold(text):
                return int(tier["tier"])
        match = re.search(r"\+(\d+)", text)
        return int(match.group(1)) // 5 if match else 0

    def owned_advancements(self, code: str) -> int:
        purchased = _int((self.character.get("characteristic_advancements") or {}).get(code))
        return self.free_advancements(code) + purchased

    def _characteristic_items(self) -> list[ShopItem]:
        rules = self.rules.get("characteristic_advancements", {})
        tiers = rules.get("tiers", [])
        bonus = _int(rules.get("bonus_per_advancement"), 5)
        maximum = _int(rules.get("max_advancements"), len(tiers))
        items = []
        characteristics = self.character.get("characteristics") or {}
        for code in CHAR_CODES:
            owned = self.owned_advancements(code)
            value = _int(characteristics.get(code))
            current_tier = tiers[owned - 1]["name"] if 0 < owned <= len(tiers) else "None"
            item = ShopItem(
                key=f"characteristic:{code}",
                category="Characteristics",
                name=CHARACTERISTIC_NAMES.get(code, code),
                cost=0,
                current=f"{value} ({current_tier})",
                description=rules.get("rule", ""),
                kind="characteristic",
                payload={"code": code, "bonus": bonus},
            )
            if owned >= maximum:
                item.blocked = "All 5 Advancements owned"
                item.next = "Maxed"
            else:
                tier = tiers[owned]
                item.cost = int(tier["experience_cost"])
                item.next = f"{value + bonus} ({tier['name']} +{bonus})"
                item.payload["tier"] = tier["name"]
            items.append(item)
        return items

    # ---------------------------------------------------------
    # Skills
    # ---------------------------------------------------------
    def _skill_records(self):
        document = self._document("skills", "skills") or {}
        return [record for record in document.get("skills", []) if isinstance(record, dict)]

    def _skill_items(self) -> list[ShopItem]:
        owned = self.character.get("skills") or {}
        levels = ((None, "trained", "Trained"), (0, "+10", "+10"), (10, "+20", "+20"))
        items = []
        for record in self._skill_records():
            name = record["name"]
            current = owned.get(name)
            current_label = (
                "Untrained" if current is None else ("Trained" if _int(current) == 0 else f"+{_int(current)}")
            )
            item = ShopItem(
                key=f"skill:{name}",
                category="Skills",
                name=name,
                cost=0,
                current=current_label,
                description=(
                    f"{record.get('difficulty', '')} skill "
                    f"({'/'.join(record.get('characteristics', []))}). "
                    f"{record.get('description', '')}"
                ).strip(),
                kind="skill",
                payload={"skill": name},
            )
            next_level = next(
                (
                    (cost_key, label)
                    for required, cost_key, label in levels
                    if (current is None and required is None)
                    or (current is not None and required is not None and _int(current) == required)
                ),
                None,
            )
            if next_level is None:
                item.blocked = "Skill is at +20"
                item.next = "Maxed"
            else:
                cost_key, label = next_level
                item.cost = _int((record.get("cost") or {}).get(cost_key))
                item.next = label
            items.append(item)
        return items

    # ---------------------------------------------------------
    # Abilities
    # ---------------------------------------------------------
    def _ability_records(self):
        document = self._document("light_abilities", "abilities") or {}
        return [record for record in document.get("abilities", []) if isinstance(record, dict)]

    def prerequisite_status(self, text) -> tuple[Optional[bool], list[str]]:
        """(True met / False unmet / None GM decides, unmet descriptions)."""
        if not text or _fold(text) in {"none", "-", "--"}:
            return True, []
        overall: Optional[bool] = True
        problems = []
        for part in str(text).split(";"):
            part = part.strip()
            if not part:
                continue
            result = self._prerequisite_part(part)
            if result is False:
                overall = False
                problems.append(part)
            elif result is None:
                if overall is not False:
                    overall = None
                problems.append(f"{part} (GM check)")
        return overall, problems

    def _prerequisite_part(self, part: str) -> Optional[bool]:
        if _fold(part).startswith("luck") or _fold(part).endswith("trait"):
            return None
        alternatives = [alt.strip() for alt in re.split(r"\s+or\s+", part) if alt.strip()]
        if len(alternatives) > 1 and ":" in alternatives[-1]:
            value = alternatives[-1].split(":", 1)[1]
            alternatives = [alt if ":" in alt else f"{alt}:{value}" for alt in alternatives]
        results = [self._prerequisite_atom(alt) for alt in alternatives]
        if any(result is True for result in results):
            return True
        if any(result is None for result in results):
            return None
        return False

    def _prerequisite_atom(self, atom: str) -> Optional[bool]:
        characteristics = self.character.get("characteristics") or {}
        skills = self.character.get("skills") or {}
        abilities = {_fold(name) for name in _as_list(self.character.get("abilities"))}

        match = re.fullmatch(r"(.+?):\s*(\d+)", atom)
        if match:
            code = CHARACTERISTIC_NAME_TO_CODE.get(_fold(match.group(1)))
            if code is None:
                return None
            return _int(characteristics.get(code)) >= int(match.group(2))

        match = re.fullmatch(r"(?:Any\s+)?(.+?)(?:\s*\(.*?\))?:\s*\+(\d+)\s+Skill.*", atom, re.I)
        if match:
            skill_name = match.group(1).strip()
            owned = next((value for name, value in skills.items() if _fold(name) == _fold(skill_name)), None)
            return owned is not None and _int(owned) >= int(match.group(2))

        match = re.fullmatch(r"(.+?)\s+Ability", atom, re.I)
        if match:
            return _fold(match.group(1)) in abilities
        return None

    def _ability_items(self) -> list[ShopItem]:
        owned = {_fold(name) for name in _as_list(self.character.get("abilities"))}
        items = []
        for record in self._ability_records():
            name = record["name"]
            prerequisite = record.get("prerequisite") or ""
            item = ShopItem(
                key=f"ability:{name}",
                category="Abilities",
                name=name,
                cost=_int(record.get("cost")),
                current="Owned" if _fold(name) in owned else "—",
                next="Learn",
                description=record.get("description", ""),
                requirement=prerequisite,
                kind="ability",
                payload={"ability": name},
            )
            if _fold(name) in owned:
                item.blocked = "Already owned"
                item.next = "Owned"
            else:
                met, problems = self.prerequisite_status(prerequisite)
                if met is False:
                    item.blocked = "Needs " + "; ".join(problems)
                elif met is None:
                    item.needs_gm = "Needs " + "; ".join(problems)
            items.append(item)
        return items

    # ---------------------------------------------------------
    # Educations
    # ---------------------------------------------------------
    def _education_records(self):
        document = self._document("educations", "educations") or {}
        records = []
        for group, label in (("general_education", "Education"), ("street_smarts", "Street Smarts")):
            for record in document.get(group, []):
                if isinstance(record, dict):
                    records.append((label, record))
        return records

    def education_limit(self) -> int:
        rules = self.rules.get("educations", {})
        multiplier = _int(rules.get("limit_intellect_modifier_multiplier"), 2)
        return self._learning_modifier() * multiplier

    def _education_items(self) -> list[ShopItem]:
        rules = self.rules.get("educations", {})
        marker = rules.get("restricted_marker", "*")
        multiplier = _int(rules.get("restricted_cost_multiplier"), 3)
        choice_markers = rules.get("choice_markers", [])
        owned = self.character.get("educations") or {}
        limit = self.education_limit()
        at_limit = len(owned) >= limit
        items = []
        for group_label, record in self._education_records():
            raw_name = record["name"]
            base_name = raw_name.rstrip(marker).strip()
            restricted = raw_name.endswith(marker)
            needs_choice = any(choice in base_name for choice in choice_markers)
            costs = record.get("cost") or {}
            learn_cost = _int(costs.get("+5"))
            upgrade_cost = _int(costs.get("+10"))
            skills = ", ".join(record.get("characteristics_or_skills", []))
            description = (
                f"{group_label} ({record.get('difficulty', '')}). Improves: {skills}. "
                f"{record.get('description', '')}"
            ).strip()
            restricted_note = rules.get("restricted_rule", "") if restricted else ""
            owned_versions = [
                name for name in owned
                if _fold(name) == _fold(base_name)
                or (needs_choice and _fold(name).startswith(_fold(base_name) + " ("))
            ]

            for owned_name in owned_versions:
                level = _int(owned[owned_name])
                item = ShopItem(
                    key=f"education:{owned_name}:+10",
                    category="Educations",
                    name=owned_name,
                    cost=upgrade_cost,
                    current=f"+{level}",
                    next="+10",
                    description=description,
                    requirement=restricted_note,
                    kind="education",
                    payload={"education": owned_name, "level": 10},
                )
                if level >= 10:
                    item.blocked = "Already +10"
                    item.next = "Maxed"
                elif restricted:
                    item.options = self._restricted_options(upgrade_cost, multiplier)
                    item.prompt = "options"
                    item.prompt_label = "Restricted Education"
                items.append(item)

            if owned_versions and not needs_choice:
                continue
            item = ShopItem(
                key=f"education:{base_name}:+5",
                category="Educations",
                name=base_name + (" (choose)" if needs_choice else ""),
                cost=learn_cost,
                current="—",
                next="+5",
                description=description,
                requirement=restricted_note,
                kind="education",
                payload={"education": base_name, "level": 5},
            )
            if at_limit:
                item.blocked = f"Education limit reached ({limit}: 2x Intellect Modifier)"
            if needs_choice:
                item.prompt = "text"
                item.prompt_label = f"Which one? (e.g. {base_name.replace('(Chosen Instrument)', '(Guitar)').replace('Faction', 'UNSC')})"
            elif restricted:
                item.prompt = "options"
                item.prompt_label = "Restricted Education"
                item.options = self._restricted_options(learn_cost, multiplier)
            if restricted:
                item.needs_gm = "Restricted: GM permission"
            items.append(item)
        return items

    @staticmethod
    def _restricted_options(cost, multiplier):
        return [
            {"label": f"The character could know this ({cost} XP)", "cost": cost, "value": "normal"},
            {"label": f"The character isn't supposed to know this ({cost * multiplier} XP)", "cost": cost * multiplier, "value": "restricted"},
        ]

    # ---------------------------------------------------------
    # Training and languages
    # ---------------------------------------------------------
    def owned_weapon_training(self) -> set[str]:
        document = self._document("weapon_training", "weapon_training") or {}
        all_training = {
            record["name"] for record in document.get("weapon_training", {}).get("training", [])
        }
        from_soldier = set()
        for value in _as_list((self.soldier or {}).get("training")):
            for name in re.split(r",|\band\b", str(value)):
                name = name.strip()
                if _fold(name) == "all":
                    from_soldier |= all_training
                elif name in all_training:
                    from_soldier.add(name)
        return from_soldier | set(_as_list(self.character.get("weapon_training")))

    def owned_faction_training(self) -> set[str]:
        rules = self.rules.get("faction_training", {})
        starting = (rules.get("starting_faction") or {}).get(
            LIGHT_AND_SKY if self.is_light_and_sky else "Core"
        )
        owned = set(_as_list(self.character.get("faction_training")))
        if starting:
            owned.add(starting)
        return owned

    def _learning_modifier(self) -> int:
        """Intellect Modifier for Education and Language limits (tripled by Acumen)."""
        intellect = _int((self.character.get("characteristics") or {}).get("INT"))
        return characteristic_modifier(intellect) * outlier_rules.learning_multiplier(
            self.game_data, self.character
        )

    def language_limit(self) -> int:
        return max(1, self._learning_modifier())

    def _training_items(self) -> list[ShopItem]:
        items = []
        document = self._document("weapon_training", "weapon_training") or {}
        owned_training = self.owned_weapon_training()
        for record in document.get("weapon_training", {}).get("training", []):
            name = record["name"]
            item = ShopItem(
                key=f"weapon_training:{name}",
                category="Training & Languages",
                name=f"{name} Weapon Training",
                cost=_int(record.get("exp")),
                current="Trained" if name in owned_training else "—",
                next="Trained",
                description="Weapons: " + ", ".join(record.get("weapons", [])),
                kind="weapon_training",
                payload={"training": name},
            )
            if name in owned_training:
                item.blocked = "Already trained"
            items.append(item)

        faction_rules = self.rules.get("faction_training", {})
        owned_factions = self.owned_faction_training()
        for faction in faction_rules.get("factions", []):
            name = faction["name"]
            item = ShopItem(
                key=f"faction_training:{name}",
                category="Training & Languages",
                name=f"{name} Faction Training",
                cost=_int(faction_rules.get("experience_cost")),
                current="Trained" if name in owned_factions else "—",
                next="Trained",
                description=faction_rules.get("rule", ""),
                kind="faction_training",
                payload={"faction": name},
            )
            if name in owned_factions:
                item.blocked = "Already trained"
            elif faction.get("gm_approval"):
                item.needs_gm = "GM must allow Forerunner training"
            items.append(item)

        language_rules = self.rules.get("languages", {})
        known = _as_list(self.character.get("languages"))
        limit = self.language_limit()
        item = ShopItem(
            key="language:new",
            category="Training & Languages",
            name="Learn a Language",
            cost=_int(language_rules.get("experience_cost"), 150),
            current=f"{1 + len(known)} known" + (f" (starting + {', '.join(known)})" if known else " (starting language)"),
            next=f"{2 + len(known)} known",
            description=language_rules.get("rule", ""),
            kind="language",
            prompt="text",
            prompt_label="Language to learn",
            suggestions=[
                name for name in language_rules.get("examples", []) if name not in known
            ],
        )
        if 1 + len(known) >= limit:
            item.blocked = f"Language limit reached ({limit}: Intellect Modifier)"
        items.append(item)
        return items

    # ---------------------------------------------------------
    # Luck and Wounds
    # ---------------------------------------------------------
    def _luck_and_wound_items(self) -> list[ShopItem]:
        items = []
        luck_rules = self.rules.get("luck", {})
        luck_total = _int(self.character.get("luck_total"))
        maximum = _int(luck_rules.get("maximum_luck"), 13)
        item = ShopItem(
            key="luck",
            category="Luck & Wounds",
            name="+1 Luck",
            cost=_int(luck_rules.get("experience_cost"), 1500),
            current=f"{luck_total} Luck",
            next=f"{luck_total + 1} Luck",
            description=luck_rules.get("rule", ""),
            kind="luck",
        )
        if luck_total >= maximum:
            item.blocked = f"Luck is at the maximum of {maximum}"
            item.next = "Maxed"
        items.append(item)

        wound_rules = self.rules.get("wound_upgrades", {})
        tiers = wound_rules.get("tiers", [])
        per_upgrade = _int(wound_rules.get("wounds_per_upgrade"), 10)
        owned = _int(self.character.get("wound_upgrades"))
        for index, tier in enumerate(tiers):
            item = ShopItem(
                key=f"wound_upgrade:{tier['name']}",
                category="Luck & Wounds",
                name=f"{tier['name']} Wound Upgrade",
                cost=_int(tier.get("experience_cost")),
                current="Owned" if index < owned else "—",
                next=f"+{per_upgrade} Wounds",
                description=wound_rules.get("rule", ""),
                kind="wound_upgrade",
                payload={"tier": index + 1, "wounds": per_upgrade, "name": tier["name"]},
            )
            if index < owned:
                item.blocked = "Already owned"
            elif index > owned:
                item.blocked = f"Buy {tiers[owned]['name']} first"
            items.append(item)
        return items

    # ---------------------------------------------------------
    # Soldier Type upgrades
    # ---------------------------------------------------------
    def _soldier_type_items(self) -> list[ShopItem]:
        items = []
        augmentations = _as_list(self.character.get("augmentations"))
        for upgrade in self.rules.get("soldier_type_upgrades", []):
            if self.soldier_key not in upgrade.get("eligible_soldier_types", []):
                continue
            name = upgrade["name"]
            bonuses = ", ".join(f"+{value} {code}" for code, value in upgrade.get("characteristic_bonuses", {}).items())
            item = ShopItem(
                key=f"soldier_upgrade:{name}",
                category="Soldier Type",
                name=name,
                cost=_int(upgrade.get("experience_cost")),
                current="Owned" if name in augmentations else "—",
                next=bonuses,
                description=f"{upgrade.get('rule', '')} Time: {upgrade.get('time', '')}.",
                kind="soldier_upgrade",
                payload={"upgrade": upgrade},
            )
            if name in augmentations:
                item.blocked = "Already owned"
            elif upgrade.get("gm_approval"):
                item.needs_gm = "GM approval"
            items.append(item)
        return items

    # ---------------------------------------------------------
    # Light & Sky: Connections
    # ---------------------------------------------------------
    def _connection_document(self):
        document = self._document("connections", "connections") or {}
        return document.get("connections", document)

    def connection_group(self, name) -> str:
        connections = self._connection_document()
        for group in ("light", "darkness", "specialized"):
            for record in connections.get(group, []):
                if _fold(record.get("name")) == _fold(name):
                    return group
        return ""

    def has_prismatic(self) -> bool:
        prismatic = self.lns_rules.get("prismatic", {}).get("connection", "Prismatic")
        return any(_fold(name) == _fold(prismatic) for name in _as_list(self.character.get("connections")))

    def _connection_items(self) -> list[ShopItem]:
        connections = self._connection_document()
        rules = connections.get("rules", {})
        owned = _as_list(self.character.get("connections"))
        owned_folded = {_fold(name) for name in owned}
        owned_groups = {self.connection_group(name) for name in owned}
        costs = {
            _int(entry.get("connection_number")): _int(entry.get("experience_cost"))
            for entry in rules.get("additional_connection_costs", [])
        }
        maximum = _int(rules.get("maximum_total_connections"), 5)
        next_number = len(owned) + 1
        required_earned = _int(self.lns_rules.get("connections", {}).get("earned_experience_required"), 2000)
        earned = self.earned_xp
        description = self.lns_rules.get("connections", {}).get("rule", "")
        items = []
        for group, label in (("light", "Light"), ("darkness", "Darkness"), ("specialized", "Specialized")):
            for record in connections.get(group, []):
                name = record["name"]
                item = ShopItem(
                    key=f"connection:{name}",
                    category="Connections",
                    name=f"{name} ({label})",
                    cost=costs.get(next_number, 0),
                    current="Owned" if _fold(name) in owned_folded else "—",
                    next=f"Connection #{next_number}",
                    description=f"{record.get('information', '')}. {description}",
                    source=LIGHT_AND_SKY,
                    kind="connection",
                    payload={"connection": name},
                )
                if _fold(name) == "prismatic":
                    item.description += " " + self.lns_rules.get("prismatic", {}).get("rule", "")
                if _fold(name) in owned_folded:
                    item.blocked = "Already owned"
                elif next_number > maximum or next_number not in costs:
                    item.blocked = f"Maximum of {maximum} Connections"
                elif group == "specialized" and not {"light", "darkness"} <= owned_groups:
                    item.blocked = "Needs a Light and a Darkness Connection"
                gm_reasons = []
                if earned is None:
                    gm_reasons.append(f"needs {required_earned:,} earned XP (creation XP unknown)")
                elif earned < required_earned and not item.blocked:
                    item.blocked = f"Needs {required_earned:,} earned XP ({earned:,} so far)"
                if group == "specialized":
                    gm_reasons.append("GM confirms the Light/Darkness interaction")
                if gm_reasons and not item.blocked:
                    item.needs_gm = "; ".join(gm_reasons)
                items.append(item)
        return items

    # ---------------------------------------------------------
    # Light & Sky: slots
    # ---------------------------------------------------------
    def _light_rules(self):
        document = self._document("light_ability_rules", "light_ability_rules") or {}
        return document.get("light_abilities", {})

    def _aspect_rules(self):
        document = self._document("light_aspect_rules", "light_aspect_rules") or {}
        return document.get("light_aspects", {}).get("rules", {})

    def guardian_class(self) -> str:
        soldier_type = str(self.character.get("soldier_type") or "")
        return soldier_type.split()[0] if soldier_type else ""

    def light_bonus(self, key: str) -> int:
        """A Light & Sky bonus from the soldier type and outliers (see LIGHT_BONUS_KEYS)."""
        if key == "bonus_light_ability_slots":
            soldier = self.class_ability_slots()
        else:
            soldier = soldier_light_bonus(self.soldier, key)
        return soldier + outlier_light_bonus(self.game_data, self.character.get("outliers"), key)

    def aspect_slots(self) -> int:
        starting = _int(self._aspect_rules().get("aspect_slots", {}).get("starting_slots"), 1)
        return (
            starting
            + self.light_bonus("bonus_aspect_slots")
            + _int(self.character.get("light_aspect_slots_purchased"))
        )

    def class_ability_slots(self) -> int:
        """Free Light Ability Slots from the soldier type (Warlock: +1)."""
        if self.soldier is not None:
            return bonus_light_ability_slots(self.soldier)
        # Soldier type not in the loaded data: fall back on the class name
        return 1 if _fold(self.guardian_class()) == "warlock" else 0

    def ability_slots(self) -> int:
        slot_rules = self._light_rules().get("rules", {}).get("ability_slots", {})
        starting = _int(slot_rules.get("starting_slots"), 2)
        return (
            starting
            + self.light_bonus("bonus_light_ability_slots")
            + _int(self.character.get("light_ability_slots_purchased"))
        )

    def _light_slot_items(self) -> list[ShopItem]:
        items = []
        aspect_rules = self._aspect_rules().get("aspect_slots", {})
        purchased_aspects = _int(self.character.get("light_aspect_slots_purchased"))
        slot_costs = aspect_rules.get("additional_slot_costs", [])
        # Free slots (Passive outlier) push each purchase one slot further along
        free_aspects = self.light_bonus("bonus_aspect_slots")
        for index, entry in enumerate(slot_costs):
            slot = _int(entry.get("slot"))
            item = ShopItem(
                key=f"aspect_slot:{slot}",
                category="Light Slots",
                name=f"Aspect Slot {slot}",
                cost=_int(entry.get("experience_cost")),
                current="Owned" if index < purchased_aspects else "—",
                next=f"{slot + free_aspects} Aspect Slots",
                description=aspect_rules.get("installation", "")
                + (f" ({free_aspects} free Aspect Slot from Outliers not counted.)" if free_aspects else ""),
                source=LIGHT_AND_SKY,
                kind="aspect_slot",
            )
            if index < purchased_aspects:
                item.blocked = "Already owned"
            elif index > purchased_aspects:
                item.blocked = f"Buy Aspect Slot {slot_costs[purchased_aspects]['slot']} first"
            items.append(item)

        slot_rules = self._light_rules().get("rules", {}).get("ability_slots", {})
        purchased_abilities = _int(self.character.get("light_ability_slots_purchased"))
        additional = _int(slot_rules.get("additional_slots"), 3)
        cost = _int(slot_rules.get("cost_per_additional_slot"), 500)
        total = self.ability_slots()
        class_slots = self.class_ability_slots()
        outlier_slots = self.light_bonus("bonus_light_ability_slots") - class_slots
        free = []
        if class_slots:
            free.append(f"{class_slots} free from {self.guardian_class() or 'soldier type'}")
        if outlier_slots:
            free.append(f"{outlier_slots} free from Outliers")
        class_note = "; ".join(free) + "; " if free else ""
        item = ShopItem(
            key="ability_slot",
            category="Light Slots",
            name="Light Ability Slot",
            cost=cost,
            current=f"{total} slots ({class_note}{purchased_abilities}/{additional} bought)",
            next=f"{total + 1} slots",
            description=slot_rules.get("installation", ""),
            source=LIGHT_AND_SKY,
            kind="ability_slot",
        )
        if purchased_abilities >= additional:
            item.blocked = f"All {additional} extra slots bought"
            item.next = "Maxed"
        items.append(item)
        return items

    # ---------------------------------------------------------
    # Light & Sky: aspects, abilities, supers
    # ---------------------------------------------------------
    def _aspect_records(self):
        document = self._document("light_aspects", "light_aspects") or {}
        for connection, records in (document.get("light_aspects") or {}).items():
            if isinstance(records, list):
                for record in records:
                    if isinstance(record, dict):
                        yield connection.title(), record

    def aspect_cost(self, record, connection) -> tuple[int, int]:
        """(cost, surcharge) - double cost for an aspect of a Connection not owned."""
        cost = _int(record.get("experience_cost"))
        owned = {_fold(name) for name in _as_list(self.character.get("connections"))}
        if _fold(connection) in owned or self.has_prismatic():
            return cost, 0
        return cost * 2, cost

    def _light_aspect_items(self) -> list[ShopItem]:
        owned = {_fold(name) for name in _as_list(self.character.get("light_aspects"))}
        items = []
        for connection, record in self._aspect_records():
            name = record["name"]
            cost, surcharge = self.aspect_cost(record, connection)
            item = ShopItem(
                key=f"light_aspect:{connection}:{name}",
                category="Light Aspects",
                name=name,
                cost=cost,
                current="Owned" if _fold(name) in owned else "—",
                next=connection,
                description=record.get("description", ""),
                requirement="Double cost: not one of your Connections" if surcharge else "",
                source=LIGHT_AND_SKY,
                kind="light_aspect",
                payload={"aspect": name, "connection": connection, "surcharge": surcharge},
            )
            if _fold(name) in owned:
                item.blocked = "Already owned"
            items.append(item)
        return items

    def _connection_matches(self, record) -> bool:
        connection = record.get("connection")
        if _fold(connection) == "universal":
            return True
        owned = _as_list(self.character.get("connections"))
        owned_folded = {_fold(name) for name in owned}
        owned_groups = {self.connection_group(name) for name in owned}
        for value in _as_list(connection) + _as_list(record.get("group")):
            if _fold(value) in owned_folded or _fold(value) in owned_groups:
                return True
        return False

    def _class_matches(self, record) -> bool:
        record_class = record.get("class")
        return record_class is None or _fold(record_class) in {"all", _fold(self.guardian_class())}

    def _light_power_records(self):
        document = self._document("light_abilities", "light_abilities_and_grenades") or {}
        for record in document.get("abilities", []):
            yield "Light Ability", record
        for record in document.get("grenades", []):
            yield "Light Grenade", record
        weapon = (self._document("light_weapon_abilities", "light_weapon_abilities") or {}).get(
            "light_weapon_abilities", {}
        ).get("base_ability")
        if isinstance(weapon, dict):
            yield "Light Ability", dict(weapon, **{"class": "All", "category": "Weapon"})

    def _power_item(self, power_type, record, is_super) -> ShopItem:
        name = record["name"]
        multiplier = self._light_rules().get("supers", {}).get("experience_cost_multiplier", 1.5)
        base_cost = _int(record.get("experience_cost"))
        cost = int(base_cost * multiplier) if is_super else base_cost
        if is_super:
            owned_list = self.character.get("supers")
        elif power_type == "Light Grenade":
            owned_list = self.character.get("light_grenades")
        else:
            owned_list = self.character.get("light_abilities")
        owned = {_fold(value) for value in _as_list(owned_list)}
        energy = record.get("light_cost", "")
        if is_super:
            energy_multiplier = self._light_rules().get("supers", {}).get("energy_cost_multiplier", 2)
            energy = (
                int(energy * energy_multiplier)
                if isinstance(energy, (int, float))
                else f"{energy_multiplier} x {energy}"
            )
        details = [
            f"{record.get('connection', '')} {power_type}",
            f"{'Super ' if is_super else 'Light '}Energy {energy}",
        ]
        if record.get("class") and _fold(record.get("class")) != "all":
            details.append(f"{record['class']} only")
        description = (
            record.get("super_description") if is_super and record.get("super_description")
            else record.get("description") or record.get("special_rules", "")
        )
        if is_super and power_type == "Light Grenade":
            description = self._light_rules().get("grenade_supers", {}).get("rule", description)
        item = ShopItem(
            key=f"{'super' if is_super else 'light_power'}:{power_type}:{name}",
            category="Supers" if is_super else "Light Abilities",
            name=name,
            cost=cost,
            current="Owned" if _fold(name) in owned else "—",
            next=" | ".join(details),
            description=description or "",
            requirement=f"{record.get('connection', '')} Connection",
            source=LIGHT_AND_SKY,
            kind="super" if is_super else "light_power",
            payload={"name": name, "power_type": power_type},
        )
        if _fold(name) in owned:
            item.blocked = "Already owned"
        elif not self._connection_matches(record):
            item.blocked = f"Needs the {record.get('connection')} Connection"
        elif not self._class_matches(record):
            item.blocked = f"{record.get('class')} only"
        return item

    def _light_ability_items(self) -> list[ShopItem]:
        return [self._power_item(kind, record, False) for kind, record in self._light_power_records()]

    def _super_items(self) -> list[ShopItem]:
        return [self._power_item(kind, record, True) for kind, record in self._light_power_records()]

    # ---------------------------------------------------------
    # Buying
    # ---------------------------------------------------------
    def find(self, key: str) -> Optional[ShopItem]:
        return next((item for item in self.all_items() if item.key == key), None)

    def can_buy(self, item: ShopItem, gm_override: bool = False, cost: Optional[int] = None) -> tuple[bool, str]:
        cost = item.cost if cost is None else cost
        if item.blocked:
            return False, item.blocked
        if item.needs_gm and not gm_override:
            return False, f"{item.needs_gm} - tick GM approval to buy"
        if cost > self.available_xp:
            return False, f"Needs {cost:,} XP ({self.available_xp:,} available)"
        return True, ""

    def buy(self, item: ShopItem, gm_override: bool = False, choice: Any = None) -> dict:
        """Apply the purchase to self.character and return its log entry."""
        cost = item.cost
        detail = ""
        if item.prompt == "options":
            option = next((opt for opt in item.options if opt["value"] == choice), None)
            if option is None:
                raise PurchaseError("Choose an option for this purchase.")
            cost = option["cost"]
            detail = option["label"]
        elif item.prompt == "text":
            choice = str(choice or "").strip()
            if not choice:
                raise PurchaseError(f"{item.prompt_label}: enter a value.")
        allowed, reason = self.can_buy(item, gm_override, cost)
        if not allowed:
            raise PurchaseError(reason)

        handler = getattr(self, f"_apply_{item.kind}")
        name = handler(item, choice) or item.name
        surcharge = item.payload.get("surcharge", 0) if item.kind == "light_aspect" else 0
        self.character["experience"] = self.available_xp - cost
        self.character["experience_spent"] = _int(self.character.get("experience_spent")) + cost
        entry = {"category": item.category, "name": name, "cost": cost}
        if detail:
            entry["detail"] = detail
        if surcharge:
            entry["surcharge"] = surcharge
        if item.needs_gm and gm_override:
            entry["gm_approved"] = item.needs_gm
        self.character.setdefault("xp_purchases", []).append(entry)
        if item.kind == "connection" and _fold(item.payload["connection"]) == "prismatic":
            refund = self._refund_aspect_surcharges()
            if refund:
                entry["refund"] = refund
        return entry

    def _refund_aspect_surcharges(self) -> int:
        refund = 0
        for entry in self.character.get("xp_purchases", []):
            surcharge = _int(entry.get("surcharge"))
            if surcharge and not entry.get("refunded"):
                refund += surcharge
                entry["refunded"] = True
        if refund:
            self.character["experience"] = self.available_xp + refund
            self.character["experience_spent"] = max(0, _int(self.character.get("experience_spent")) - refund)
        return refund

    # Handlers return the name recorded in the purchase log (or None).
    def _apply_characteristic(self, item, choice):
        code = item.payload["code"]
        max_before = self._max_wounds()
        characteristics = self.character.setdefault("characteristics", {})
        characteristics[code] = _int(characteristics.get(code)) + item.payload["bonus"]
        advancements = self.character.setdefault("characteristic_advancements", {})
        advancements[code] = _int(advancements.get(code)) + 1
        self._keep_wounds_in_step(max_before)
        return f"{item.name} {item.payload['tier']} Advancement"

    def _apply_skill(self, item, choice):
        skills = self.character.setdefault("skills", {})
        skill = item.payload["skill"]
        skills[skill] = 0 if skill not in skills else _int(skills[skill]) + 10
        return f"{skill} {item.next}"

    def _apply_ability(self, item, choice):
        self.character.setdefault("abilities", []).append(item.payload["ability"])

    def _apply_education(self, item, choice):
        educations = self.character.setdefault("educations", {})
        name = item.payload["education"]
        if item.prompt == "text":
            base = re.sub(r"\s*\(.*?\)\s*$", "", name) if "(Chosen" in name else name
            name = f"{base} ({choice})"
            if name in educations:
                raise PurchaseError(f"{name} is already known.")
        educations[name] = item.payload["level"]
        return f"{name} +{item.payload['level']}"

    def _apply_weapon_training(self, item, choice):
        self.character.setdefault("weapon_training", []).append(item.payload["training"])

    def _apply_faction_training(self, item, choice):
        self.character.setdefault("faction_training", []).append(item.payload["faction"])

    def _apply_language(self, item, choice):
        languages = self.character.setdefault("languages", [])
        if any(_fold(language) == _fold(choice) for language in languages):
            raise PurchaseError(f"{choice} is already known.")
        languages.append(choice)
        return f"Language: {choice}"

    def _apply_luck(self, item, choice):
        self.character["luck_total"] = _int(self.character.get("luck_total")) + 1
        self.character["luck_available"] = _int(self.character.get("luck_available")) + 1

    def _apply_wound_upgrade(self, item, choice):
        wounds = item.payload["wounds"]
        self.character["wound_upgrades"] = _int(self.character.get("wound_upgrades")) + 1
        self.character["wounds_modifier"] = _int(self.character.get("wounds_modifier")) + wounds
        self.character["wounds"] = _int(self.character.get("wounds")) + wounds

    def _apply_soldier_upgrade(self, item, choice):
        upgrade = item.payload["upgrade"]
        max_before = self._max_wounds()
        characteristics = self.character.setdefault("characteristics", {})
        for code, value in upgrade.get("characteristic_bonuses", {}).items():
            characteristics[code] = _int(characteristics.get(code)) + _int(value)
        source = upgrade.get("mythic_characteristics_from")
        record = self.game_data.get("soldier_type", source) if source and self.game_data else None
        if record:
            mythic = self.character.setdefault("mythic_characteristics", {})
            for code, value in (record.get("mythic_characteristics") or {}).items():
                mythic[code] = f"+{max(mythic_value(mythic.get(code)), mythic_value(value))}"
        self.character.setdefault("augmentations", []).append(upgrade["name"])
        self._keep_wounds_in_step(max_before)

    def _apply_connection(self, item, choice):
        self.character.setdefault("connections", []).append(item.payload["connection"])
        return f"{item.payload['connection']} Connection"

    def _apply_aspect_slot(self, item, choice):
        self.character["light_aspect_slots_purchased"] = _int(self.character.get("light_aspect_slots_purchased")) + 1

    def _apply_ability_slot(self, item, choice):
        self.character["light_ability_slots_purchased"] = _int(self.character.get("light_ability_slots_purchased")) + 1

    def _apply_light_aspect(self, item, choice):
        self.character.setdefault("light_aspects", []).append(item.payload["aspect"])

    def _apply_light_power(self, item, choice):
        field_name = "light_grenades" if item.payload["power_type"] == "Light Grenade" else "light_abilities"
        self.character.setdefault(field_name, []).append(item.payload["name"])

    def _apply_super(self, item, choice):
        self.character.setdefault("supers", []).append(item.payload["name"])
        return f"{item.payload['name']} (Super)"

    def _max_wounds(self) -> int:
        characteristics = self.character.get("characteristics") or {}
        mythic = self.character.get("mythic_characteristics") or {}
        return max_wounds(
            _int(characteristics.get("TOU")),
            mythic.get("TOU", 0),
            _as_list(self.character.get("outliers")).count("Robust"),
            flat_bonus=_int(self.character.get("wounds_modifier")),
        )

    def _keep_wounds_in_step(self, max_before: int):
        """Current Wounds rise with Max Wounds when Toughness goes up."""
        gained = self._max_wounds() - max_before
        if gained > 0:
            self.character["wounds"] = _int(self.character.get("wounds")) + gained


def snapshot(character: dict) -> dict:
    return copy.deepcopy(character)
