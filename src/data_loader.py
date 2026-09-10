import json
from pathlib import Path

from .game_data import GameData
from .validators.base_validator import BaseValidator


class DataLoader:
    """
    Loads JSON files from /data/core and optionally /data/light_and_sky.
    Identifies document families, validates them, and returns a unified GameData object.
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

    def __init__(self, use_light_and_sky: bool = False):
        self.use_light_and_sky = use_light_and_sky
        self.core_root = Path("data/core")
        self.lns_root = Path("data/light_and_sky")

    # ---------------------------------------------------------
    # Main loader
    # ---------------------------------------------------------
    def load_all(self):
        game_data = GameData()
        validator = BaseValidator(game_data)

        # -----------------------------
        # CORE MODE
        # -----------------------------
        if not self.use_light_and_sky:
            # Load UNSC soldier types
            self._load_folder(self.core_root / "unsc_soldier_types", game_data, validator)

            # Load upbringing/environment/lifestyle
            self._load_folder(self.core_root / "upbringing_envionment_lifestyle", game_data, validator)

            # Load other core rule folders
            self._load_folder(self.core_root, game_data, validator)

        # -----------------------------
        # LIGHT & SKY MODE
        # -----------------------------
        else:
            # Load human soldier types (Awoken, Exo, Human)
            self._load_folder(self.lns_root / "character_creation" / "human_soldier_types",
                              game_data, validator)

            # Load Guardian classes + subclasses
            self._load_folder(self.lns_root / "character_creation" / "guardian_classes_subclasses",
                              game_data, validator)

            # Load other Light & Sky rule folders
            self._load_folder(self.lns_root, game_data, validator)

        return game_data


    # ---------------------------------------------------------
    # Folder loader
    # ---------------------------------------------------------
    def _load_folder(self, root: Path, game_data: GameData, validator: BaseValidator):
        if not root.exists():
            game_data.record_error(f"Missing data folder: {root}")
            return

        for path in root.rglob("*.json"):
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

            name = path.stem

            # Store raw document
            doc["source_path"] = path.as_posix()
            game_data.add_document(family, name, doc)

            # Validate
            self.validate_document(family, name, doc, validator)

    # ---------------------------------------------------------
    # Family detection
    # ---------------------------------------------------------
    def identify_family(self, doc: dict):
        # Soldier types can also contain keys such as "training".
        if "base_characteristics" in doc:
            return "soldier_type"

        for key in doc.keys():
            if key in self.FAMILY_MAP:
                return self.FAMILY_MAP[key]

        return None

    # ---------------------------------------------------------
    # Validation
    # ---------------------------------------------------------
    def validate_document(self, family, name, doc, validator):
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
