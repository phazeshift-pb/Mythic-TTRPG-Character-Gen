from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Any

from .background_choices import choice_groups, resolve_modifiers
from .derived_stats import max_wounds
from . import outliers as outlier_rules


CHAR_CODES = ["STR", "TOU", "AGI", "WFR", "WFM", "INT", "PER", "CRG", "CHA", "LDR"]
MYTHIC_CHAR_CODES = ("STR", "TOU", "AGI")

CHARACTERISTIC_NAME_TO_CODE = {
    "strength": "STR",
    "toughness": "TOU",
    "agility": "AGI",
    "warfare range": "WFR",
    "warfare melee": "WFM",
    "intellect": "INT",
    "perception": "PER",
    "courage": "CRG",
    "charisma": "CHA",
    "leadership": "LDR",
}

# Mythic 7.0: an Upbringing, Environment or Lifestyle option can't be taken
# if it would lower a Characteristic to 5 or below.
BACKGROUND_FLOOR = 5


class BackgroundFloorError(ValueError):
    """A background option would lower a Characteristic to 5 or below."""


_MODIFIER_PATTERN = re.compile(r"^\s*([+-]\d+)\s+(.+?)\s*$")
_ADVANCEMENT_PATTERN = re.compile(r"([+-]\d+)")


def advancement_bonus(value: Any) -> int:
    """Characteristic bonus of a Soldier Type advancement such as '+10 Rookie'."""
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        match = _ADVANCEMENT_PATTERN.search(value)
        if match:
            return int(match.group(1))
    return 0


@dataclass
class Character:
    """
    Core runtime character model for Mythic TTRPG.
    This object is the result of character creation and is used by
    the generator, UI, and gameplay systems.
    """

    # Identity
    name: str = "Unnamed Character"
    soldier_type: Optional[str] = None

    # Core stats
    characteristics: Dict[str, int] = field(default_factory=lambda: {c: 0 for c in CHAR_CODES})
    mythic_characteristics: Dict[str, Any] = field(default_factory=dict)

    # Skills
    skills: Dict[str, int] = field(default_factory=dict)  # 0 = trained, 10 = +10, 20 = +20
    abilities: List[str] = field(default_factory=list)

    # Background
    upbringing: Optional[str] = None
    environment: Optional[str] = None
    lifestyle: Optional[str] = None
    # One entry per lifestyle applied: {"name", "roll", "choices"}
    lifestyle_results: List[Dict[str, Any]] = field(default_factory=list)

    # Meta
    wounds: int = 0
    wounds_modifier: int = 0  # flat +/- Wounds from backgrounds (e.g. Street Urchin)
    fatigue: int = 0
    rank: Optional[str] = None
    credits: int = 0
    experience: int = 0
    starting_experience: int = 0
    experience_spent: int = 0
    experience_tier: Optional[int] = None

    # Equipment
    equipment: List[str] = field(default_factory=list)
    equipment_pack: Optional[str] = None
    armor: Optional[str] = None
    # Spartans: {"name", "generation", "price"} of the Mjolnir variant fitted,
    # and the characteristic bonuses the worn suit grants (see starting_armor).
    armor_variant: Optional[Dict[str, Any]] = None
    armor_bonus: Dict[str, int] = field(default_factory=dict)
    # Light & Sky: the full roll of worn engram armor (see src/loot/character_loot.py)
    armor_loot: Optional[Dict[str, Any]] = None
    # Toggled on the character sheet; bonuses apply only while worn.
    armor_equipped: bool = True
    # Core: {"name", "quantity", "nickname", "note", "category"} dicts naming
    # UNSC Armory records (see src/models/equipment_packs.py).
    weapons: List[Any] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    specialization_packs: List[str] = field(default_factory=list)
    outliers: List[str] = field(default_factory=list)  # one entry per time taken
    # Aptitude / Forte: the Characteristic picked for each time taken
    outlier_choices: Dict[str, List[str]] = field(default_factory=dict)
    support_points: int = 0  # Advocate adds 2; set the Rank's SP on the sheet
    luck_available: int = 0
    luck_total: int = 0
    light_aspects: List[str] = field(default_factory=list)
    light_abilities: List[str] = field(default_factory=list)
    light_grenades: List[str] = field(default_factory=list)
    supers: List[str] = field(default_factory=list)

    # Post-creation XP purchases (see src/models/xp_shop.py)
    creation_experience: Optional[int] = None  # XP the character was created with
    characteristic_advancements: Dict[str, int] = field(default_factory=dict)  # bought tiers
    educations: Dict[str, int] = field(default_factory=dict)  # name -> 5 or 10
    languages: List[str] = field(default_factory=list)  # learned beyond the starting language
    weapon_training: List[str] = field(default_factory=list)  # bought beyond the Soldier Type's
    faction_training: List[str] = field(default_factory=list)
    wound_upgrades: int = 0  # Iron, Copper, Bronze, Steel, Titanium bought (in order)
    augmentations: List[str] = field(default_factory=list)  # e.g. ORION Augmentation
    light_aspect_slots_purchased: int = 0
    light_ability_slots_purchased: int = 0
    xp_purchases: List[Dict[str, Any]] = field(default_factory=list)  # purchase log

    # Internal debug log
    debug_log: List[str] = field(default_factory=list)

    # -----------------------------
    # Logging helper
    # -----------------------------
    def log(self, message: str):
        self.debug_log.append(message)

    # -----------------------------
    # Apply Soldier Type
    # -----------------------------
    def apply_soldier_type(self, soldier_data: dict):
        self.soldier_type = soldier_data.get("name")
        self.log(f"Applying soldier type: {self.soldier_type}")

        # Base characteristics
        for code, value in soldier_data.get("base_characteristics", {}).items():
            if isinstance(value, (int, float)):
                self.characteristics[code] = int(value)
                self.log(f"Set {code} = {value}")

        self.apply_soldier_type_advancements(soldier_data)

        # Mythic characteristics
        self.mythic_characteristics = dict(soldier_data.get("mythic_characteristics", {}))

        special = soldier_data.get("special_rules")
        special = special if isinstance(special, dict) else {}

        # Rank: the explicit starting_rank wins over the trait's wording
        if special.get("starting_rank"):
            self.rank = str(special["starting_rank"])
            self.log(f"Rank set to {self.rank}")
        else:
            for trait in soldier_data.get("traits", []):
                if trait["name"].lower() == "rank":
                    self.rank = (
                        trait["effect"].replace("Begins at Rank:", "").strip().rstrip(".")
                    )
                    self.log(f"Rank set to {self.rank}")

        # Abilities a trait grants at creation (e.g. Spartans' Fast Foot)
        for ability in special.get("starting_abilities") or []:
            if ability not in self.abilities:
                self.abilities.append(ability)
                self.log(f"Soldier Type ability: {ability}")

        # Support Points a trait grants at creation (e.g. ONI Section I +1)
        if special.get("support_points"):
            self.support_points += int(special["support_points"])
            self.log(f"Soldier Type Support Points: +{int(special['support_points'])}")

        # Equipment sets (not applied automatically)
        # You will apply these in the generator pipeline.

    def apply_soldier_type_advancements(self, soldier_data: dict):
        """Add the Characteristic Advancements a Soldier Type unlocks at creation.

        e.g. a Marine's "+10 Rookie" Warfare Range adds +10 WFR. These count as
        owned tiers in the XP Shop, so they are never bought again.
        """
        for code, value in (soldier_data.get("advancements") or {}).items():
            bonus = advancement_bonus(value)
            if bonus and code in self.characteristics:
                self.characteristics[code] += bonus
                self.log(f"Soldier Type advancement: {code} {value} ({bonus:+d})")

    # -----------------------------
    # Apply Upbringing
    # -----------------------------
    def apply_upbringing(self, upbringing_data: dict, choices=None):
        self.upbringing = upbringing_data["name"]
        self.log(f"Applying upbringing: {self.upbringing}")
        self._apply_background(upbringing_data, choices)

    # -----------------------------
    # Apply Environment
    # -----------------------------
    def apply_environment(self, env_data: dict, choices=None):
        self.environment = env_data["name"]
        self.log(f"Applying environment: {self.environment}")
        self._apply_background(env_data, choices)

    def _apply_background(self, record: dict, choices=None):
        """Apply fixed modifiers plus the player's pick from each choice group."""
        modifiers, problems = resolve_modifiers(record, choices)
        for problem in problems:
            self.log(problem)
        self._check_background_floor(record.get("name", "This option"), modifiers)
        for modifier in modifiers:
            self._apply_modifier(modifier)

    def _check_background_floor(self, source: str, modifiers):
        """Raise BackgroundFloorError if the modifiers lower any Characteristic to 5 or below."""
        totals = dict(self.characteristics)
        lowered = set()
        for text in modifiers:
            match = _MODIFIER_PATTERN.match(text) if isinstance(text, str) else None
            if match is None:
                continue
            code = CHARACTERISTIC_NAME_TO_CODE.get(match.group(2).casefold())
            if code in totals:
                totals[code] += int(match.group(1))
                if int(match.group(1)) < 0:
                    lowered.add(code)
        too_low = sorted(code for code in lowered if totals[code] <= BACKGROUND_FLOOR)
        if too_low:
            details = ", ".join(f"{code} {totals[code]}" for code in too_low)
            raise BackgroundFloorError(
                f"{source} can't be taken: it would lower {details} "
                f"(a background option can't lower a Characteristic to "
                f"{BACKGROUND_FLOOR} or below)."
            )

    # -----------------------------
    # Apply Lifestyle
    # -----------------------------
    def apply_lifestyle(self, lifestyle_data: dict, roll: int, choose=None):
        """Apply the outcome matching roll.

        If that outcome has choice groups (e.g. Hunter's "+3 to chosen
        Warfare Characteristic"), choose(lifestyle_data, roll, groups) is
        called and must return one option label per group.
        """
        self.lifestyle = lifestyle_data["name"]
        self.log(f"Applying lifestyle: {self.lifestyle} (roll={roll})")

        for outcome in lifestyle_data["outcomes"]:
            low, high = self._parse_roll_range(outcome["roll"])
            if low <= roll <= high:
                groups = choice_groups(outcome)
                choices = list(choose(lifestyle_data, roll, groups)) if groups and choose else []
                resolved = dict(outcome, name=f"{self.lifestyle} (roll {roll})")
                modifiers, problems = resolve_modifiers(resolved, choices)
                for problem in problems:
                    self.log(problem)
                self._check_background_floor(resolved["name"], modifiers)
                for modifier in modifiers:
                    self._apply_modifier(modifier)
                self.lifestyle_results.append(
                    {"name": self.lifestyle, "roll": roll, "choices": choices}
                )
                break

    # -----------------------------
    # Apply Specialization Pack
    # -----------------------------
    def apply_specialization_pack(self, pack_data: dict):
        pack_name = pack_data["name"]
        if pack_name not in self.specialization_packs:
            self.specialization_packs.append(pack_name)
        self.log(f"Applying specialization pack: {pack_name}")

        for ability in pack_data.get("abilities", []):
            if ability not in self.abilities:
                self.abilities.append(ability)
                self.log(f"Specialization ability: {ability}")

        for skill_entry in pack_data.get("skills", []):
            match = re.fullmatch(r"(.+?)\s+\((Trained|\+\d+)\)", skill_entry)
            if not match:
                self.log(f"Failed to parse specialization skill: {skill_entry}")
                continue

            skill_name, level_text = match.groups()
            target_level = 0 if level_text == "Trained" else int(level_text[1:])
            if skill_name not in self.skills:
                self.train_skill(skill_name)
            while self.skills[skill_name] < target_level:
                self.upgrade_skill(skill_name)
            self.log(f"Specialization skill: {skill_name} (+{self.skills[skill_name]})")

    def apply_outlier(
        self, outlier_data: dict, luck_cost: int, characteristic: Optional[str] = None
    ):
        """Take an outlier once (call again to take it again where the book allows).

        Aptitude and Forte need ``characteristic``: the code that gains the bonus.
        A take beyond the outlier's limit is ignored and logged.
        """
        outlier_name = outlier_data["name"]
        choice_kind = outlier_rules.needs_choice(outlier_data)
        # Records without limit fields (older data, tests) behave as before
        if choice_kind is None and outlier_name in {"Aptitude", "Forte"}:
            choice_kind = "characteristic" if outlier_name == "Aptitude" else "mythic"
            outlier_data = dict(
                outlier_data,
                **{
                    "max_times_per_characteristic"
                    if choice_kind == "characteristic"
                    else "max_times_per_mythic": 2
                },
            )
        choices = self.outlier_choices.get(outlier_name, [])
        if not outlier_rules.can_take(outlier_data, self.outliers, choices, characteristic):
            if choice_kind == "characteristic" and characteristic not in CHAR_CODES:
                raise ValueError(f"{outlier_name} requires a valid characteristic code.")
            if choice_kind == "mythic" and characteristic not in MYTHIC_CHAR_CODES:
                raise ValueError(f"{outlier_name} requires a valid mythic characteristic code.")
            self.log(f"Outlier not applied (limit reached): {outlier_name} {characteristic or ''}")
            return

        if choice_kind == "characteristic":
            if characteristic not in CHAR_CODES:
                raise ValueError(f"{outlier_name} requires a valid characteristic code.")
            bonus = int(outlier_data.get("chosen_characteristic_bonus", 5))
            self.characteristics[characteristic] += bonus
            self.log(f"{outlier_name}: +{bonus} {characteristic}")
        elif choice_kind == "mythic":
            if characteristic not in MYTHIC_CHAR_CODES:
                raise ValueError(f"{outlier_name} requires a valid mythic characteristic code.")
            current_value = self.mythic_characteristics.get(characteristic, 0)
            try:
                new_value = int(current_value) + int(outlier_data.get("chosen_mythic_bonus", 1))
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid mythic characteristic value for {characteristic}: "
                    f"{current_value!r}"
                ) from error
            self.mythic_characteristics[characteristic] = f"+{new_value}"
            self.log(f"{outlier_name}: +1 Mythic {characteristic} (now +{new_value})")
        if choice_kind:
            self.outlier_choices.setdefault(outlier_name, []).append(characteristic)

        for code, value in (outlier_data.get("characteristic_bonus") or {}).items():
            if code in self.characteristics:
                self.characteristics[code] += int(value)
                self.log(f"{outlier_name}: {int(value):+d} {code}")
        if outlier_data.get("support_points"):
            self.support_points += int(outlier_data["support_points"])
            self.log(f"{outlier_name}: +{int(outlier_data['support_points'])} Support Points")

        self.outliers.append(outlier_name)
        self.luck_total -= luck_cost
        self.luck_available = min(self.luck_available, self.luck_total)
        self.compute_wounds()
        times = self.outliers.count(outlier_name)
        self.log(
            f"Applying outlier: {outlier_name}"
            f"{f' (x{times})' if times > 1 else ''} "
            f"(Burn Luck: {luck_cost}; effect: "
            f"{outlier_rules.effect_text(outlier_data, times)})"
        )

    def clear_outliers(self, outlier_records: Optional[Dict[str, dict]] = None):
        """Undo the outlier effects not rebuilt by the creator (Support Points), then forget them.

        The creator restores Characteristics, Mythics and Luck itself before
        re-applying the current picks.
        """
        by_name = {
            str(name).casefold(): record for name, record in (outlier_records or {}).items()
        }
        for name in self.outliers:
            points = int((by_name.get(name.casefold()) or {}).get("support_points") or 0)
            self.support_points = max(0, self.support_points - points)
        self.outliers = []
        self.outlier_choices = {}

    def apply_equipment_pack(
        self,
        pack_name: str,
        items: List[str],
        weapons: Optional[List[dict]] = None,
        armor: Optional[str] = None,
    ):
        """Set the pack's gear (``items``), armory ``weapons`` and worn ``armor``."""
        self.equipment_pack = pack_name
        self.equipment = list(items)
        self.weapons = [dict(weapon) for weapon in weapons or []]
        self.armor = armor
        self.log(
            f"Applying equipment pack: {pack_name} "
            f"({len(self.weapons)} weapons, {len(items)} items)"
        )
        if armor:
            self.log(f"Armor: {armor}")
        for weapon in self.weapons:
            quantity = weapon.get("quantity", 1)
            self.log(f"Weapon: {weapon['name']}" + (f" x{quantity}" if quantity != 1 else ""))
        for item in items:
            self.log(f"Equipment: {item}")

    def apply_starting_armor(
        self,
        armor: str,
        variant: Optional[dict] = None,
        bonus: Optional[Dict[str, int]] = None,
    ):
        """Wear a Spartan's chosen suit; bonuses are recorded, not added to base stats."""
        self.armor = armor
        self.armor_variant = dict(variant) if variant else None
        self.armor_bonus = dict(bonus or {})
        self.log(f"Starting armor: {armor}")
        if variant:
            self.log(
                f"Mjolnir variant: {variant['name']} ({variant['generation']}, "
                f"{variant.get('price', 0)} cR)"
            )
        if self.armor_bonus:
            self.log(f"Armor bonuses while worn: {self.armor_bonus}")

    def apply_light_powers(
        self,
        aspects: List[dict],
        abilities: List[dict],
        supers: Optional[List[dict]] = None,
    ):
        supers = supers or []
        self.light_aspects = [aspect["name"] for aspect in aspects]
        selected_abilities = [
            ability
            for ability in abilities
            if ability.get("_power_type") != "Light Grenade"
        ]
        selected_grenades = [
            ability
            for ability in abilities
            if ability.get("_power_type") == "Light Grenade"
        ]
        self.light_abilities = [ability["name"] for ability in selected_abilities]
        self.light_grenades = [grenade["name"] for grenade in selected_grenades]
        self.supers = [super_power["name"] for super_power in supers]
        for aspect in aspects:
            self.log(
                f"Light Aspect: {aspect['name']} "
                f"(XP {aspect.get('experience_cost', 0)}): {aspect['description']}"
            )
        for ability in abilities:
            power_type = ability.get("_power_type", "Light Ability")
            description = ability.get("description") or ability.get("special_rules", "")
            self.log(
                f"{power_type}: {ability['name']} "
                f"(XP {ability.get('experience_cost', 0)}, "
                f"Light {ability.get('light_cost', 'N/A')}): {description}"
            )
        for super_power in supers:
            description = super_power.get("super_description") or ""
            self.log(
                f"Super: {super_power['name']} "
                f"(XP {super_power.get('experience_cost', 0)}, "
                f"Super Energy {super_power.get('super_energy_cost', 'N/A')}): "
                f"{description}"
            )

    # -----------------------------
    # Skill Training
    # -----------------------------
    def train_skill(self, skill_name: str):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0
            self.log(f"Trained skill: {skill_name}")

    def upgrade_skill(self, skill_name: str):
        if skill_name not in self.skills:
            self.log(f"Cannot upgrade untrained skill: {skill_name}")
            return

        current = self.skills[skill_name]
        if current < 20:
            self.skills[skill_name] = current + 10
            self.log(f"Upgraded skill {skill_name} to +{self.skills[skill_name]}")

    # -----------------------------
    # Modifier Parsing
    # -----------------------------
    def _apply_modifier(self, text: str):
        """
        Applies modifiers like '+5 Strength' or '-3 Courage'.
        """
        match = _MODIFIER_PATTERN.match(text) if isinstance(text, str) else None
        if match is None:
            self.log(f"Failed to parse modifier: {text!r}")
            return

        value = int(match.group(1))
        target = match.group(2).casefold()
        if target == "wounds":
            self.wounds_modifier += value
            self.log(f"Applied modifier: {text} -> Wounds {value:+d}")
            return
        code = CHARACTERISTIC_NAME_TO_CODE.get(target)
        if code is None or code not in self.characteristics:
            self.log(f"Unsupported modifier target (not applied): {text!r}")
            return

        self.characteristics[code] += value
        self.log(f"Applied modifier: {text} -> {code} {value:+d}")

    def _parse_roll_range(self, roll_text: str):
        """
        Converts '1-5' or '10' into numeric ranges.
        """
        if "-" in roll_text:
            low, high = roll_text.split("-")
            return int(low), int(high)
        return int(roll_text), int(roll_text)

    # -----------------------------
    # Derived Stats
    # -----------------------------
    def compute_wounds(self):
        """Maximum Wounds per data/character_creation/wounds_formula.json."""
        self.wounds = max_wounds(
            self.characteristics["TOU"],
            self.mythic_characteristics.get("TOU", 0),
            list(self.outliers).count("Robust"),
            flat_bonus=self.wounds_modifier,
        )
        self.log(f"Computed wounds = {self.wounds}")

    def compute_fatigue(self):
        """Fatigue is a damage-style track: new characters start with none."""
        self.fatigue = 0
        self.log(f"Computed fatigue = {self.fatigue}")

    # -----------------------------
    # Finalization
    # -----------------------------
    def finalize(self):
        self.compute_wounds()
        self.compute_fatigue()
        self.log("Character finalized.")
