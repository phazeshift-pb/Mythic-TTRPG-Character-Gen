import json
from pathlib import Path

from .game_data import GameData
from .validators.base_validator import BaseValidator


class DataLoader:
    """
    Loads all JSON files under /data, identifies document families,
    validates them, and returns a unified GameData object.
    """

    FAMILY_MAP = {
        "skills": "skills",
        "upbringing": "upbringing",
        "environment": "environment",
        "lifestyle": "lifestyle",
        "experience_tiers": "experience_tiers",
        "creation_points": "creation_points",
        "languages": "languages",
        "connections": "connections",
        "characteristics": "characteristics",
        "actions": "actions",
        "equipment_packs": "equipment_packs",
        "weapon_training": "weapon_training",
        "special_rules": "special_rules",
        "hit_locations": "hit_locations",
        "medical_effects": "medical_effects",
        "wounds": "wounds",
        "damage": "damage",
        "defense": "defense",
        "training": "training",
        "terrain": "terrain",
        "weather": "weather",
        "lighting": "lighting",
        "movement_stealth_modifiers": "movement_stealth_modifiers",
        "passive_perception": "passive_perception",
        "radar": "radar",
        "visr": "visr",
        "iff": "iff",
        "smartlink": "smartlink",
        "camouflage": "camouflage",
        "active_camouflage": "active_camouflage",
        "listening": "listening",
        "cover": "cover",
        "pierce": "pierce",
        "scatter": "scatter",
        "initiative": "initiative",
        "speed_combat": "speed_combat",
        "time": "time",
        "turn_structure": "turn_structure",
        "attack_limits": "attack_limits",
        "attack_sequence": "attack_sequence"
    }

    def __init__(self, data_root="data"):
        self.data_root = Path(data_root)

    def load_all(self):
        game_data = GameData()
        validator = BaseValidator(game_data)

        for path in self.data_root.rglob("*.json"):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception as e:
                game_data.record_error(f"{path}: JSON load error: {e}")
                continue

            # Identify document family
            family = self.identify_family(doc)
            if not family:
                game_data.record_error(f"{path}: unknown document family")
                continue

            # Name resolution
            name = path.stem

            # Store raw document
            game_data.add_document(family, name, doc)

            # Validate
            self.validate_document(family, name, doc, validator)

        return game_data

    def identify_family(self, doc: dict):
        """
        Determine document family based on top-level keys.
        """
        for key in doc.keys():
            if key in self.FAMILY_MAP:
                return self.FAMILY_MAP[key]

        # Soldier types have "name" and characteristic maps
        if "base_characteristics" in doc:
            return "soldier_type"

        return None

    def validate_document(self, family, name, doc, validator):
        """
        Family-specific validation.
        """

        if family == "soldier_type":
            bc = doc.get("base_characteristics")
            if bc:
                validator.validate_characteristic_map(
                    f"{name}.base_characteristics", bc
                )

            mc = doc.get("mythic_characteristics")
            if mc:
                validator.validate_characteristic_map(
                    f"{name}.mythic_characteristics", mc
                )

            adv = doc.get("advancements")
            if adv:
                validator.validate_characteristic_map(
                    f"{name}.advancements", adv
                )

        if family == "skills":
            for skill in doc.get("skills", []):
                if "name" not in skill:
                    validator.require(False, f"{name}: skill missing name")

                if "characteristics" in skill:
                    for ch in skill["characteristics"]:
                        validator.require(
                            ch in validator.CHARACTERISTIC_CODES,
                            f"{name}: skill '{skill['name']}' invalid characteristic '{ch}'"
                        )
