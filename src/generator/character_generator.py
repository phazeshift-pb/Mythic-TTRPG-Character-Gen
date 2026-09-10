import random
from typing import Optional

from ..models.character import Character


class CharacterGenerator:
    """
    Clean separation between Core and Light & Sky modes.

    Core mode:
        - UNSC soldier types
        - upbringing/environment/lifestyle
        - no human soldier types
        - no guardian classes/subclasses

    Light & Sky mode:
        - human soldier types
        - guardian classes + subclasses
        - no upbringing/environment/lifestyle
        - no UNSC soldier types
    """

    def __init__(self, game_data, use_light_and_sky: bool = False):
        self.data = game_data
        self.use_light_and_sky = use_light_and_sky

    # ---------------------------------------------------------
    # Public API
    # ---------------------------------------------------------
    def generate(
        self,
        name: str,
        soldier_type: str,
        subclass: Optional[str] = None,
        upbringing: Optional[str] = None,
        environment: Optional[str] = None,
        lifestyle: Optional[str] = None,
        lifestyle_roll: Optional[int] = None,
        auto_assign_skills: bool = True,
        human_soldier_type: Optional[str] = None,
        guardian_class: Optional[str] = None,
    ) -> Character:

        char = Character(name=name)

        # Soldier Type (expansion-aware)
        self._apply_soldier_type(
            char,
            soldier_type,
            subclass,
            human_soldier_type=human_soldier_type,
            guardian_class=guardian_class,
        )

        # -----------------------------
        # CORE MODE ONLY
        # -----------------------------
        if not self.use_light_and_sky:
            if upbringing:
                self._apply_upbringing(char, upbringing)

            if environment:
                self._apply_environment(char, environment)

            if lifestyle:
                self._apply_lifestyle(char, lifestyle, lifestyle_roll)

        # -----------------------------
        # LIGHT & SKY MODE ONLY
        # -----------------------------
        else:
            char.log("Light & Sky mode: ignoring upbringing/environment/lifestyle.")

            soldier_record = self.data.get("soldier_type", soldier_type)
            is_guardian = soldier_record and "guardian_classes_subclasses" in soldier_record.get("source_path", "")
            if is_guardian and subclass is None:
                char.log("ERROR: Guardian subclass required in Light & Sky mode.")

        # Skills
        if auto_assign_skills:
            self._auto_assign_skills(char)

        # Equipment
        self._apply_equipment(char)

        # Finalize derived stats
        char.finalize()

        return char

    # ---------------------------------------------------------
    # Soldier Type (Core vs Light & Sky)
    # ---------------------------------------------------------
    def _apply_soldier_type(
        self,
        char: Character,
        soldier_type_name: str,
        subclass: Optional[str],
        human_soldier_type: Optional[str] = None,
        guardian_class: Optional[str] = None,
    ):
        soldier_types = self.data.families.get("soldier_type", {})

        core_types = {}
        human_types = {}
        guardian_types = {}

        # Categorize based on source_path
        for name, record in soldier_types.items():
            path = record.get("source_path", "")

            if "core/unsc_soldier_types" in path:
                core_types[name] = record

            if "light_and_sky/character_creation/human_soldier_types" in path:
                human_types[name] = record

            if "light_and_sky/character_creation/guardian_classes_subclasses" in path:
                guardian_types[name] = record

        # -----------------------------
        # CORE MODE
        # -----------------------------
        if not self.use_light_and_sky:
            if soldier_type_name not in core_types:
                char.log(f"'{soldier_type_name}' is not a core UNSC soldier type.")
                return

            char.apply_soldier_type(core_types[soldier_type_name])
            return

        # -----------------------------
        # LIGHT & SKY MODE
        # -----------------------------
        # Light & Sky combines the human foundation with a guardian class.
        human_name = human_soldier_type or (
            soldier_type_name if soldier_type_name in human_types else None
        )
        guardian_name = guardian_class or (
            soldier_type_name if soldier_type_name in guardian_types else None
        )

        if human_name:
            char.apply_soldier_type(human_types[human_name])

        if guardian_name:
            guardian = guardian_types[guardian_name]
            char.soldier_type = guardian.get("name")
            char.log(f"Applying guardian class: {char.soldier_type}")

            for code, value in guardian.get("base_characteristics", {}).items():
                modifier = self._numeric_value(value)
                if modifier is not None:
                    char.characteristics[code] += modifier
                    char.log(f"Guardian class modifier: {code} +{modifier}")

            char.mythic_characteristics.update(guardian.get("mythic_characteristics", {}))

            subclasses = guardian.get("subclasses", {})
            if subclass not in subclasses:
                char.log(f"Guardian subclass '{subclass}' not found.")
                return

            sub_data = subclasses[subclass]
            char.log(f"Applying Guardian subclass: {subclass}")

            for code, value in sub_data.get("characteristic_modifiers", {}).items():
                modifier = self._numeric_value(value)
                if modifier is not None:
                    char.characteristics[code] += modifier
                    char.log(f"Subclass modifier: {code} {modifier:+d}")

            return

        char.log(f"'{soldier_type_name}' is not available in Light & Sky mode.")

    @staticmethod
    def _numeric_value(value):
        if isinstance(value, (int, float)):
            return int(value)

        if isinstance(value, str):
            try:
                return int(value.strip().replace("+", "", 1))
            except ValueError:
                return None

        return None

    # ---------------------------------------------------------
    # Upbringing (CORE ONLY)
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
    # Environment (CORE ONLY)
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
    # Lifestyle (CORE ONLY)
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
        skills_doc = self.data.get("skills", "skills")
        if not skills_doc:
            char.log("Skills data missing.")
            return

        all_skills = [s["name"] for s in skills_doc.get("skills", [])]

        chosen = random.sample(all_skills, 4)
        for skill in chosen:
            char.train_skill(skill)

        char.log(f"Auto-trained skills: {', '.join(chosen)}")

    # ---------------------------------------------------------
    # Equipment (expansion-aware)
    # ---------------------------------------------------------
    def _apply_equipment(self, char: Character):
        soldier_data = self.data.get("soldier_type", char.soldier_type)
        if not soldier_data:
            return

        sets = soldier_data.get("equipment_sets", {})
        if not sets:
            char.log("No equipment sets found.")
            return

        first_set_name = next(iter(sets))
        items = sets[first_set_name]

        filtered_items = []
        for item in items:
            if not self.use_light_and_sky and item.startswith("LNS_"):
                continue
            filtered_items.append(item)

        char.equipment.extend(filtered_items)
        char.log(f"Applied equipment set '{first_set_name}' with {len(filtered_items)} items.")
