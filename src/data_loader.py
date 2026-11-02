import json
from pathlib import Path

from .game_data import GameData
from .validators.base_validator import BaseValidator


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_ROOT = REPO_ROOT / "data"


class DataLoader:
    """
    Loads JSON files from data/core and optionally data/light_and_sky.
    Identifies document families, validates them, and returns a unified GameData object.

    Paths are resolved from the repository, not the current working
    directory, so the app and tools work no matter where they are launched.
    """

    FAMILY_MAP = {
        "skills": "skills",
        "upbringing": "upbringing",
        "environment": "environment",
        "lifestyle": "lifestyle",
        "experience_tiers": "experience_tiers",
        "wounds_formula": "wounds_formula",
        "perceptive_range": "perceptive_range",
        "creation_points": "creation_points",
        "specialization_packs": "specialization_packs",
        "outliers": "outliers",
        "light_aspects": "light_aspects",
        "light_abilities": "light_abilities",
        "abilities": "light_abilities",
        "languages": "languages",
        "connections": "connections",
        "characteristics": "characteristics",
        "modifier_rules": "characteristic_modifiers",
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
        "movement_speeds": "movement_speeds",
        "encumbrance": "encumbrance",
        "characteristic_modifiers": "characteristic_modifiers",
        "mythic": "mythic_characteristics",
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
        "attack_sequence": "attack_sequence",
        # XP Shop rules and Educations (both rulesets)
        "xp_shop": "xp_shop",
        "general_education": "educations",
        # Light & Sky equipment and weapon abilities
        "armor_perks": "lns_armor_perks",
        "perks": "lns_weapon_perks",
        "plasteel_armor_table": "lns_armor",
        "elements": "lns_elements",
        "hand_cannons": "lns_weapons",
        "light_weapon_abilities": "light_weapon_abilities",
        # Core UNSC Armory
        "unsc_weapons": "unsc_weapons",
        "unsc_explosives": "unsc_explosives",
        "unsc_armor": "unsc_armor",
        "mjolnir_variants": "unsc_armor_variants",
        "armor_permutations": "unsc_armor_permutations",
    }

    def __init__(self, use_light_and_sky: bool = False, data_root=None):
        self.use_light_and_sky = use_light_and_sky
        self.data_root = Path(data_root) if data_root else DEFAULT_DATA_ROOT
        self.character_creation_root = self.data_root / "character_creation"
        self.core_root = self.data_root / "core"
        self.lns_root = self.data_root / "light_and_sky"
        self._loaded_paths = set()

    # ---------------------------------------------------------
    # Main loader
    # ---------------------------------------------------------
    def load_all(self):
        game_data = GameData()
        validator = BaseValidator(game_data)
        self._loaded_paths = set()
        data = self.data_root
        self._load_folder(self.character_creation_root, game_data, validator)
        self._load_folder(data / "characteristics.json", game_data, validator)
        self._load_folder(data / "abilities.json", game_data, validator)
        self._load_folder(data / "skills.json", game_data, validator)
        self._load_folder(data / "educations.json", game_data, validator)
        self._load_folder(data / "xp_shop.json", game_data, validator)
        self._load_folder(
            data / "movement/movement_speeds.json", game_data, validator
        )
        self._load_folder(
            data / "movement/encumbrance.json", game_data, validator
        )
        self._load_folder(
            data / "hiding_spotting_visr/passive_perception.json",
            game_data,
            validator,
        )
        self._load_folder(
            data / "perceptive_range.json", game_data, validator
        )
        self._load_folder(
            data / "characteristic_modifiers.json", game_data, validator
        )
        self._load_folder(
            data / "mythic_characteristics.json", game_data, validator
        )
        # Fatigue penalties and Natural Healing (Enduring / Vigorous on the sheet)
        self._load_folder(
            data / "wounds_medical/wounds.json", game_data, validator
        )

        # -----------------------------
        # CORE MODE
        # -----------------------------
        if not self.use_light_and_sky:
            # Load UNSC soldier types
            self._load_folder(self.core_root / "unsc_soldier_types", game_data, validator)

            # Load upbringing/environment/lifestyle
            self._load_folder(self.core_root / "upbringing_environment_lifestyle", game_data, validator)

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
            self._load_folder(self.lns_root, game_data, validator, exclude_names={"outliers"})
            self._load_folder(
                self.lns_root / "character_creation" / "outliers.json",
                game_data,
                validator,
                name_prefix="light_and_sky",
            )

        return game_data


    # ---------------------------------------------------------
    # Folder loader
    # ---------------------------------------------------------
    def _load_folder(
        self,
        root: Path,
        game_data: GameData,
        validator: BaseValidator,
        exclude_names=None,
        name_prefix=None,
    ):
        if not root.exists():
            game_data.record_error(f"Missing data folder: {self._display_path(root)}")
            return

        paths = [root] if root.is_file() else sorted(root.rglob("*.json"))
        for path in paths:
            if path.stem in (exclude_names or set()):
                continue
            resolved = path.resolve()
            if resolved in self._loaded_paths:
                continue  # already loaded by a more specific call
            self._loaded_paths.add(resolved)
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

            name = f"{name_prefix}_{path.stem}" if name_prefix else path.stem
            source_path = self._display_path(path)

            existing = game_data.get(family, name)
            if existing is not None and existing.get("source_path") != source_path:
                game_data.record_error(
                    f"{source_path}: duplicate {family} name '{name}' "
                    f"(already loaded from {existing.get('source_path')})"
                )
                continue

            # Store raw document
            doc["source_path"] = source_path
            game_data.add_document(family, name, doc)

            # Validate
            self.validate_document(family, name, doc, validator)

    def _display_path(self, path: Path) -> str:
        """'data/...'-style path, matching what saved data has always used."""
        try:
            return path.resolve().relative_to(self.data_root.parent).as_posix()
        except ValueError:
            return path.as_posix()

    # ---------------------------------------------------------
    # Family detection
    # ---------------------------------------------------------
    def identify_family(self, doc: dict):
        # Soldier types can also contain keys such as "training".
        if "base_characteristics" in doc:
            return "soldier_type"

        if "light_aspects" in doc and "rules" in doc["light_aspects"]:
            return "light_aspect_rules"

        if "light_abilities" in doc and "rules" in doc["light_abilities"]:
            return "light_ability_rules"

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
                            validator.characteristic_code(ch) is not None,
                            f"{name}: skill '{skill.get('name')}' invalid characteristic '{ch}'"
                        )
