import random
from typing import Optional

from models.character import Character


class CharacterGenerator:
    """
    The orchestrator for Mythic TTRPG character creation.
    Uses GameData + Character model to build a complete character.
    """

    def __init__(self, game_data):
        self.data = game_data

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def generate(
        self,
        name: str,
        soldier_type: str,
        upbringing: Optional[str] = None,
        environment: Optional[str] = None,
        lifestyle: Optional[str] = None,
        lifestyle_roll: Optional[int] = None,
        auto_assign_skills: bool = True
    ) -> Character:

        char = Character(name=name)

        # Soldier Type
        self._apply_soldier_type(char, soldier_type)

        # Upbringing
        if upbringing:
            self._apply_upbringing(char, upbringing)

        # Environment
        if environment:
            self._apply_environment(char, environment)

        # Lifestyle
        if lifestyle:
            self._apply_lifestyle(char, lifestyle, lifestyle_roll)

        # Skills
        if auto_assign_skills:
            self._auto_assign_skills(char)

        # Equipment
        self._apply_equipment(char)

        # Finalize derived stats
        char.finalize()

        return char

    # ---------------------------------------------------------
    # Soldier Type
    # ---------------------------------------------------------
    def _apply_soldier_type(self, char: Character, soldier_type_name: str):
        soldier_data = self.data.get("soldier_type", soldier_type_name)
        if not soldier_data:
            char.log(f"Soldier type '{soldier_type_name}' not found.")
            return

        char.apply_soldier_type(soldier_data)

    # ---------------------------------------------------------
    # Upbringing
    # ---------------------------------------------------------
    def _apply_upbringing(self, char: Character, name: str):
        records = self.data.get("upbringing", "upbringing")
        if not records:
            char.log("Upbringing data missing.")
            return

        for record in records.get("upbringing", []):
            if record["name"].lower() == name.lower():
                char.apply_upbringing(record)
                return

        char.log(f"Upbringing '{name}' not found.")

    # ---------------------------------------------------------
    # Environment
    # ---------------------------------------------------------
    def _apply_environment(self, char: Character, name: str):
        records = self.data.get("environment", "environment")
        if not records:
            char.log("Environment data missing.")
            return

        for record in records.get("environment", []):
            if record["name"].lower() == name.lower():
                char.apply_environment(record)
                return

        char.log(f"Environment '{name}' not found.")

    # ---------------------------------------------------------
    # Lifestyle
    # ---------------------------------------------------------
    def _apply_lifestyle(self, char: Character, name: str, roll: Optional[int]):
        records = self.data.get("lifestyle", "lifestyle")
        if not records:
            char.log("Lifestyle data missing.")
            return

        for record in records.get("lifestyle", []):
            if record["name"].lower() == name.lower():
                if roll is None:
                    roll = random.randint(1, 10)
                    char.log(f"Lifestyle roll auto-generated: {roll}")

                char.apply_lifestyle(record, roll)
                return

        char.log(f"Lifestyle '{name}' not found.")

    # ---------------------------------------------------------
    # Auto Skill Assignment
    # ---------------------------------------------------------
    def _auto_assign_skills(self, char: Character):
        """
        Soldier Types often grant:
        - 4 trained skills
        - Weapon training
        - Faction training
        This function assigns basic trained skills automatically.
        """

        skills_doc = self.data.get("skills", "skills")
        if not skills_doc:
            char.log("Skills data missing.")
            return

        all_skills = [s["name"] for s in skills_doc.get("skills", [])]

        # Auto-train 4 random skills (placeholder logic)
        chosen = random.sample(all_skills, 4)
        for skill in chosen:
            char.train_skill(skill)

        char.log(f"Auto-trained skills: {', '.join(chosen)}")

    # ---------------------------------------------------------
    # Equipment
    # ---------------------------------------------------------
    def _apply_equipment(self, char: Character):
        """
        Soldier Types define equipment sets.
        This function applies the default set (first one).
        """

        soldier_data = self.data.get("soldier_type", char.soldier_type)
        if not soldier_data:
            return

        sets = soldier_data.get("equipment_sets", {})
        if not sets:
            char.log("No equipment sets found.")
            return

        # Pick the first equipment set
        first_set_name = next(iter(sets))
        items = sets[first_set_name]

        char.equipment.extend(items)
        char.log(f"Applied equipment set '{first_set_name}' with {len(items)} items.")
