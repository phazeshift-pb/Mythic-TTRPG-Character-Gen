from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Any

from .background_choices import choice_groups, resolve_modifiers
from .derived_stats import max_wounds


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

_MODIFIER_PATTERN = re.compile(r"^\s*([+-]\d+)\s+(.+?)\s*$")


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
    weapons: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)
    specialization_packs: List[str] = field(default_factory=list)
    outliers: List[str] = field(default_factory=list)
    luck_available: int = 0
    luck_total: int = 0
    light_aspects: List[str] = field(default_factory=list)
    light_abilities: List[str] = field(default_factory=list)
    light_grenades: List[str] = field(default_factory=list)
    supers: List[str] = field(default_factory=list)

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

        # Mythic characteristics
        self.mythic_characteristics = soldier_data.get("mythic_characteristics", {})

        # Rank
        for trait in soldier_data.get("traits", []):
            if trait["name"].lower() == "rank":
                self.rank = trait["effect"].replace("Begins at Rank:", "").strip()
                self.log(f"Rank set to {self.rank}")

        # Equipment sets (not applied automatically)
        # You will apply these in the generator pipeline.

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
        for modifier in modifiers:
            self._apply_modifier(modifier)

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
        outlier_name = outlier_data["name"]
        if outlier_name not in self.outliers:
            if outlier_name == "Aptitude":
                if characteristic not in CHAR_CODES:
                    raise ValueError("Aptitude requires a valid characteristic code.")
                self.characteristics[characteristic] += 5
                self.log(f"Aptitude: +5 {characteristic}")
            elif outlier_name == "Forte":
                if characteristic not in MYTHIC_CHAR_CODES:
                    raise ValueError(
                        "Forte requires a valid mythic characteristic code."
                    )
                current_value = self.mythic_characteristics.get(characteristic, 0)
                try:
                    new_value = int(current_value) + 1
                except (TypeError, ValueError) as error:
                    raise ValueError(
                        f"Invalid mythic characteristic value for {characteristic}: "
                        f"{current_value!r}"
                    ) from error
                self.mythic_characteristics[characteristic] = f"+{new_value}"
                self.log(f"Forte: +1 Mythic {characteristic} (now +{new_value})")

            self.outliers.append(outlier_name)
            self.luck_total -= luck_cost
            self.luck_available = min(self.luck_available, self.luck_total)
            self.compute_wounds()
        self.log(
            f"Applying outlier: {outlier_name} "
            f"(Burn Luck: {luck_cost}; effect: {outlier_data['effect']})"
        )

    def apply_equipment_pack(self, pack_name: str, items: List[str]):
        self.equipment_pack = pack_name
        self.equipment = list(items)
        self.log(f"Applying equipment pack: {pack_name} ({len(items)} items)")
        for item in items:
            self.log(f"Equipment: {item}")

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
