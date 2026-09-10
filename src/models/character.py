from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any


CHAR_CODES = ["STR", "TOU", "AGI", "WFR", "WFM", "INT", "PER", "CRG", "CHA", "LDR"]


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

    # Background
    upbringing: Optional[str] = None
    environment: Optional[str] = None
    lifestyle: Optional[str] = None

    # Meta
    wounds: int = 0
    fatigue: int = 0
    rank: Optional[str] = None
    credits: int = 0
    experience: int = 0
    starting_experience: int = 0
    experience_spent: int = 0
    experience_tier: Optional[int] = None

    # Equipment
    equipment: List[str] = field(default_factory=list)
    armor: Optional[str] = None
    weapons: List[str] = field(default_factory=list)
    connections: List[str] = field(default_factory=list)

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
    def apply_upbringing(self, upbringing_data: dict):
        self.upbringing = upbringing_data["name"]
        self.log(f"Applying upbringing: {self.upbringing}")

        for bonus in upbringing_data.get("bonuses", []):
            self._apply_modifier(bonus)

        for penalty in upbringing_data.get("penalties", []):
            self._apply_modifier(penalty)

    # -----------------------------
    # Apply Environment
    # -----------------------------
    def apply_environment(self, env_data: dict):
        self.environment = env_data["name"]
        self.log(f"Applying environment: {self.environment}")

        for bonus in env_data.get("bonuses", []):
            self._apply_modifier(bonus)

        for penalty in env_data.get("penalties", []):
            self._apply_modifier(penalty)

    # -----------------------------
    # Apply Lifestyle
    # -----------------------------
    def apply_lifestyle(self, lifestyle_data: dict, roll: int):
        self.lifestyle = lifestyle_data["name"]
        self.log(f"Applying lifestyle: {self.lifestyle} (roll={roll})")

        # Find matching outcome
        for outcome in lifestyle_data["outcomes"]:
            low, high = self._parse_roll_range(outcome["roll"])
            if low <= roll <= high:
                for bonus in outcome.get("bonuses", []):
                    self._apply_modifier(bonus)
                for penalty in outcome.get("penalties", []):
                    self._apply_modifier(penalty)
                break

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
        Applies modifiers like '+5 Strength' or '-3 Charisma'.
        """
        try:
            parts = text.split()
            value = int(parts[0])
            stat = parts[1].upper()[:3]  # STR, TOU, AGI, etc.

            if stat in self.characteristics:
                self.characteristics[stat] += value
                self.log(f"Applied modifier: {text}")
        except Exception:
            self.log(f"Failed to parse modifier: {text}")

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
        """
        Basic wounds formula (placeholder).
        You will replace this with your actual rule document.
        """
        self.wounds = self.characteristics["TOU"] + self.characteristics["STR"]
        self.log(f"Computed wounds = {self.wounds}")

    def compute_fatigue(self):
        self.fatigue = self.characteristics["TOU"] // 10
        self.log(f"Computed fatigue = {self.fatigue}")

    # -----------------------------
    # Finalization
    # -----------------------------
    def finalize(self):
        self.compute_wounds()
        self.compute_fatigue()
        self.log("Character finalized.")
