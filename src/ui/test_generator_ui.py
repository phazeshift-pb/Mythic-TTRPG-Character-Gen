from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from PySide6.QtWidgets import (
    QApplication, QDialog, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QGridLayout, QInputDialog, QMessageBox, QFileDialog,
)

from PySide6.QtCore import Qt
from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.character import CHAR_CODES, MYTHIC_CHAR_CODES
from src.models.derived_stats import (
    ROBUST_WOUNDS,
    WOUNDS_BASE,
    WOUNDS_PER_MYTHIC_TOUGHNESS,
    WOUNDS_PER_TOUGHNESS_MODIFIER,
    max_wounds,
    mythic_value,
)
from src.ui.character_setup_home import CharacterSetupHome
from src.ui.debug_page import DebugPage
from src.ui.equipment_page import EquipmentPage
from src.ui.landing_page import LandingPage
from src.ui.initial_character_setup import InitialCharacterSetupPage
from src.ui.interactive_character_sheet import InteractiveCharacterSheet
from src.ui.outlier_page import OutlierPage
from src.ui.specialization_page import DelayedTooltipLabel, SpecializationPage
from src.ui.skill_training_dialog import SkillTrainingDialog
from src.ui.stat_allocation import StatAllocationPage
from src.ui.version_and_expansions import VersionAndExpansionsPage


class TestGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mythic TTRPG Character Manager")
        self.resize(900, 650)

        layout = QVBoxLayout(self)
        self.pages = QStackedWidget()

        self.landing_page = LandingPage()
        self.character_setup_home = CharacterSetupHome()
        self.version_and_expansions_page = VersionAndExpansionsPage()
        self.initial_character_setup_page = InitialCharacterSetupPage()
        self.creation_page = StatAllocationPage()
        self.specialization_page = SpecializationPage()
        self.outlier_page = OutlierPage()
        self.equipment_page = EquipmentPage()
        self.debug_page = DebugPage()
        self.character_sheet = InteractiveCharacterSheet()
        self.page_widgets = (
            self.landing_page,
            self.character_setup_home,
            self.version_and_expansions_page,
            self.initial_character_setup_page,
            self.creation_page,
            self.outlier_page,
            self.specialization_page,
            self.equipment_page,
            self.debug_page,
            self.character_sheet,
        )
        for page in self.page_widgets:
            self.pages.addWidget(page)
        layout.addWidget(self.pages)

        self.create_character_button = self.landing_page.create_character_button
        self.load_character_button = self.landing_page.load_character_button
        self.load_character_button.clicked.connect(self.load_character)
        self.character_sheet.home_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.landing_page)
        )
        self.character_sheet.save_requested.connect(self.save_loaded_character)
        self.character_setup_home.finish_character_button.clicked.connect(
            self.finish_and_name_character
        )

        self.experience_input = self.character_setup_home.experience_input
        self.experience_tier_label = self.character_setup_home.experience_tier_label
        self.soldier_combo = self.initial_character_setup_page.soldier_combo
        self.upbringing_combo = self.initial_character_setup_page.upbringing_combo
        self.environment_combo = self.initial_character_setup_page.environment_combo
        self.lifestyle_combos = self.initial_character_setup_page.lifestyle_combos
        self.human_combo = self.initial_character_setup_page.human_combo
        self.guardian_combo = self.initial_character_setup_page.guardian_combo
        self.subclass_combo = self.initial_character_setup_page.subclass_combo
        self.connection_combo = self.initial_character_setup_page.connection_combo
        self.generate_button = self.initial_character_setup_page.generate_button

        self.back_button = self.creation_page.back_button
        self.creation_points_combo = self.creation_page.creation_points_combo
        self.reset_creation_button = self.creation_page.reset_creation_button
        self.creation_points_remaining_label = (
            self.creation_page.creation_points_remaining_label
        )
        self.characteristic_grid = self.creation_page.characteristic_grid
        self.characteristic_value_labels = (
            self.creation_page.characteristic_value_labels
        )
        self.characteristic_buttons = self.creation_page.characteristic_buttons
        self.next_button = self.creation_page.next_button

        self.specialization_back_button = self.specialization_page.back_button
        self.specialization_done_button = self.specialization_page.next_button
        self.specialization_done_button.setEnabled(False)
        self.specialization_scroll = self.specialization_page.scroll_area
        self.specialization_content = self.specialization_page.content
        self.specialization_grid = self.specialization_page.grid
        self.specialization_tiles = self.specialization_page.tiles

        self.outlier_back_button = self.outlier_page.back_button
        self.outlier_done_button = self.outlier_page.done_button
        self.outlier_scroll = self.outlier_page.scroll_area
        self.outlier_content = self.outlier_page.content
        self.outlier_grid = self.outlier_page.grid
        self.outlier_tiles = self.outlier_page.tiles

        self.equipment_page_title = self.equipment_page.title
        self.equipment_back_button = self.equipment_page.back_button
        self.equipment_done_button = self.equipment_page.done_button
        self.equipment_scroll = self.equipment_page.scroll_area
        self.equipment_content = self.equipment_page.content
        self.equipment_grid = self.equipment_page.grid
        self.equipment_tiles = self.equipment_page.tiles
        self.light_aspect_tiles = self.equipment_page.light_aspect_tiles
        self.light_ability_tiles = self.equipment_page.light_ability_tiles
        self._selected_light_category = None
        self._selected_light_aspects = {}
        self._selected_light_powers = {}
        self._selected_light_supers = {}
        self._light_xp_spent = 0
        self._starting_luck = 0
        self.equipment_page.light_category_selected.connect(
            self.select_light_category
        )

        self.create_character_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.character_setup_home)
        )
        self.character_setup_home.version_and_expansions_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.version_and_expansions_page)
        )
        self.character_setup_home.initial_setup_button.clicked.connect(
            self.open_initial_setup_from_home
        )
        self.character_setup_home.stat_point_allocation_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.character_setup_home.outliers_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.character_setup_home.debug_button.clicked.connect(
            self.open_debug_page
        )
        self.character_setup_home.specialization_packs_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.character_setup_home.equipment_or_light_powers_button.clicked.connect(
            self.open_equipment_page
        )
        self.version_and_expansions_page.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.character_setup_home)
        )
        self.version_and_expansions_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )
        self.version_and_expansions_page.continue_button.clicked.connect(
            self.open_initial_setup_from_version
        )
        self.experience_input.valueChanged.connect(self.update_experience_tier)
        self.version_and_expansions_page.mode_changed.connect(
            self._handle_version_selection_changed
        )
        self.upbringing_combo.currentIndexChanged.connect(
            self.refresh_core_background_options
        )
        self.human_combo.currentIndexChanged.connect(self.refresh_selection_options)
        self.guardian_combo.currentIndexChanged.connect(self.update_subclasses)
        self.generate_button.clicked.connect(self.generate_character)
        self.initial_character_setup_page.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.version_and_expansions_page)
        )
        self.initial_character_setup_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )
        self.initial_character_setup_page.option_selected.connect(
            self.select_initial_setup_option
        )
        self.initial_character_setup_page.selection_requirements_changed.connect(
            self.character_setup_home.set_initial_setup_complete
        )
        self.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.initial_character_setup_page)
        )
        self.creation_points_combo.currentIndexChanged.connect(
            self.reset_creation_points
        )
        self.reset_creation_button.clicked.connect(self.reset_creation_points)
        self.next_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.specialization_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.specialization_done_button.clicked.connect(
            self.finish_specialization_selection
        )
        self.outlier_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.outlier_done_button.clicked.connect(self.finish_outlier_selection)
        self.equipment_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.equipment_done_button.clicked.connect(self.finish_equipment_selection)
        for page in (
            self.creation_page,
            self.specialization_page,
            self.outlier_page,
            self.equipment_page,
        ):
            page.home_button.clicked.connect(self.return_to_character_setup_home)
        self.debug_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )

        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self._selected_soldier_skills = {}
        self._outlier_characteristics = {}
        self._loaded_character_path = None

        self.update_soldier_types()
        self._build_specialization_pack_tiles()
        self._build_outlier_tiles()
        self._build_equipment_tiles()
        self._refresh_initial_setup_options()

    def open_initial_setup_from_home(self):
        self.pages.setCurrentWidget(self.initial_character_setup_page)

    def open_initial_setup_from_version(self):
        self.pages.setCurrentWidget(self.initial_character_setup_page)

    def return_to_character_setup_home(self):
        self.pages.setCurrentWidget(self.character_setup_home)

    def open_debug_page(self):
        self.debug_page.set_report(self._build_debug_report())
        self.pages.setCurrentWidget(self.debug_page)

    def load_character(self):
        characters_directory = Path(__file__).resolve().parents[2] / "characters"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Load Character",
            str(characters_directory),
            "Character files (*.json)",
        )
        if not file_path:
            return

        try:
            export_data = json.loads(
                Path(file_path).read_text(encoding="utf-8")
            )
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
            QMessageBox.critical(
                self,
                "Character Load Failed",
                f"Could not load the character file:\n{error}",
            )
            return

        if not isinstance(export_data, dict) or not isinstance(
            export_data.get("character"), dict
        ):
            QMessageBox.warning(
                self,
                "Invalid Character File",
                "The selected file does not contain a valid character export.",
            )
            return

        ruleset = str(export_data.get("ruleset") or "")
        character_game_data = self.game_data
        if (ruleset == "Light & Sky") != (self.selected_mode == "Light & Sky"):
            character_game_data = DataLoader(
                use_light_and_sky=ruleset == "Light & Sky"
            ).load_all()

        self.character_sheet.set_character(
            export_data["character"], ruleset, character_game_data
        )
        self._loaded_character_path = Path(file_path)
        self.character_sheet.set_save_available(True)
        self.pages.setCurrentWidget(self.character_sheet)

    def save_loaded_character(self):
        file_path = self._loaded_character_path
        if file_path is None:
            QMessageBox.warning(
                self,
                "Character Not Loaded",
                "Load a character file before saving changes.",
            )
            return

        temporary_path = None
        try:
            export_data = json.loads(file_path.read_text(encoding="utf-8"))
            if not isinstance(export_data, dict) or not isinstance(
                export_data.get("character"), dict
            ):
                QMessageBox.warning(
                    self,
                    "Invalid Character File",
                    "The character file no longer contains a valid character export.",
                )
                return

            export_data["character"] = (
                self.character_sheet.character_data_for_save()
            )
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=file_path.parent,
                prefix=f".{file_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(export_data, temporary_file, indent=2, ensure_ascii=False)
                temporary_file.write("\n")
            os.replace(temporary_path, file_path)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, TypeError) as error:
            if temporary_path is not None:
                try:
                    temporary_path.unlink()
                except FileNotFoundError:
                    pass
                except OSError:
                    pass
            QMessageBox.critical(
                self,
                "Character Save Failed",
                f"Could not save changes to the character file:\n{error}",
            )
            return

        QMessageBox.information(
            self,
            "Character Saved",
            f"Character saved to:\n{file_path}",
        )

    def _handle_version_selection_changed(self, mode):
        self.character_setup_home.set_version_selected(mode is not None)
        self.character_setup_home.set_character_ready_to_export(False)
        self.update_soldier_types()

    def _character_export_data(self):
        # Stat allocation and outliers change Toughness after generation.
        self.generated_character.compute_wounds()
        character_data = asdict(self.generated_character)
        character_data.pop("debug_log", None)
        use_light_and_sky = self.selected_mode == "Light & Sky"

        def selected_value(combo):
            return combo.currentData() or combo.currentText() or None

        if use_light_and_sky:
            selected_soldier_types = (
                selected_value(self.human_combo),
                selected_value(self.guardian_combo),
            )
            initial_setup = {
                "human_soldier_type": selected_soldier_types[0],
                "guardian_soldier_type": selected_soldier_types[1],
                "subclass": selected_value(self.subclass_combo),
                "connection": selected_value(self.connection_combo),
                "skill_training": {
                    soldier_type: self._selected_soldier_skills[soldier_type]
                    for soldier_type in selected_soldier_types
                    if soldier_type in self._selected_soldier_skills
                },
            }
            equipment = {
                "light_aspects": [
                    aspect["name"]
                    for aspect, _ in self._selected_light_aspects.values()
                ],
                "light_abilities": [
                    power["name"]
                    for power in self._selected_light_powers.values()
                ],
                "supers": [
                    power["name"]
                    for power in self._selected_light_supers.values()
                ],
            }
        else:
            initial_setup = {
                "soldier_type": selected_value(self.soldier_combo),
                "upbringing": selected_value(self.upbringing_combo),
                "environment": selected_value(self.environment_combo),
                "lifestyles": [
                    selected_value(combo)
                    for combo in self.lifestyle_combos
                    if selected_value(combo)
                ],
                "skill_training": self._selected_soldier_skills.get(
                    selected_value(self.soldier_combo), {}
                ),
            }
            equipment = {
                "pack": next(
                    (
                        name
                        for button, name, _ in self.equipment_tiles
                        if button.isChecked()
                    ),
                    None,
                )
            }

        return {
            "format_version": 1,
            "ruleset": self.selected_mode,
            "character": character_data,
            "selections": {
                "starting_xp": self.experience_input.value(),
                "initial_setup": initial_setup,
                "creation_points": {
                    "option": self.creation_points_combo.currentText(),
                    "total": self.creation_points_combo.currentData(),
                    "allocations": self._creation_allocations.copy(),
                },
                "outliers": [
                    outlier["name"]
                    for button, outlier, _ in self.outlier_tiles
                    if button.isChecked()
                ],
                "outlier_characteristics": {
                    outlier_name: characteristic
                    for outlier_name, characteristic
                    in self._outlier_characteristics.items()
                    if outlier_name in self._selected_outlier_names()
                },
                "specialization_packs": [
                    name
                    for button, name in self.specialization_tiles
                    if button.isChecked()
                ],
                "equipment": equipment,
            },
        }

    def finish_and_name_character(self):
        if not hasattr(self, "generated_character"):
            QMessageBox.warning(
                self,
                "Character Not Ready",
                "Complete character creation before exporting.",
            )
            return

        character_name, accepted = QInputDialog.getText(
            self,
            "Finish and Name Your Character",
            "Character name:",
            text=self.generated_character.name,
        )
        if not accepted:
            return
        character_name = character_name.strip()
        file_name = re.sub(
            r'[<>:"/\\|?*\x00-\x1f]', "_", character_name
        ).strip(" .")
        if not file_name:
            QMessageBox.warning(
                self,
                "Invalid Character Name",
                "Enter a name that can be used as a file name.",
            )
            return

        characters_directory = Path(__file__).resolve().parents[2] / "characters"
        output_path = characters_directory / f"{file_name}.json"
        if output_path.exists():
            answer = QMessageBox.question(
                self,
                "Replace Character File?",
                f"{output_path.name} already exists. Replace it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        original_name = self.generated_character.name
        self.generated_character.name = character_name
        export_data = self._character_export_data()
        try:
            characters_directory.mkdir(parents=True, exist_ok=True)
            output_path.write_text(
                json.dumps(export_data, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as error:
            self.generated_character.name = original_name
            QMessageBox.critical(
                self,
                "Character Export Failed",
                f"Could not save the character file:\n{error}",
            )
            return

        QMessageBox.information(
            self,
            "Character Exported",
            f"Character saved to:\n{output_path}",
        )

    @staticmethod
    def _selected_option(combo):
        return combo.currentText() or "None"

    @staticmethod
    def _selected_tile_names(tiles, name_index=1):
        return [
            tile[name_index]
            for tile in tiles
            if tile[0].isChecked()
        ]

    def _selected_outlier_names(self):
        return [
            outlier["name"]
            for tile, outlier, _ in self.outlier_tiles
            if tile.isChecked()
        ]

    @staticmethod
    def _mythic_value(character, code):
        value = character.mythic_characteristics.get(code, 0)
        if isinstance(value, str):
            return int(value.strip())
        return int(value) if isinstance(value, (int, float)) else 0

    @staticmethod
    def _rule_multiplier(formula, default):
        separator = "*" if "*" in formula else "×" if "×" in formula else None
        if separator is None:
            return default
        return int(formula.rsplit(separator, 1)[1].strip())

    def _outlier_record(self, name):
        document = self.game_data.get("outliers", "outliers") or {}
        return next(
            (
                outlier
                for outlier in document.get("outliers", {}).get("list", [])
                if outlier.get("name") == name
            ),
            {},
        )

    def _build_debug_report(self):
        lines = [
            "CHARACTER GENERATION INPUTS",
            f"Ruleset: {self.selected_mode}",
            f"Starting experience: {self.experience_input.value():,} XP",
            self.experience_tier_label.text(),
        ]

        if self.selected_mode == "Light & Sky":
            lines.extend(
                (
                    f"Human soldier type: {self._selected_option(self.human_combo)}",
                    f"Guardian class: {self._selected_option(self.guardian_combo)}",
                    f"Subclass: {self._selected_option(self.subclass_combo)}",
                    f"Connection: {self._selected_option(self.connection_combo)}",
                )
            )
        else:
            lines.extend(
                (
                    f"Soldier type: {self._selected_option(self.soldier_combo)}",
                    f"Upbringing: {self._selected_option(self.upbringing_combo)}",
                    f"Environment: {self._selected_option(self.environment_combo)}",
                    "Lifestyles: "
                    + ", ".join(
                        self._selected_option(combo)
                        for combo in self.lifestyle_combos
                        if combo.currentText()
                    ),
                )
            )

        lines.extend(
            (
                f"Creation point option: {self.creation_points_combo.currentText() or 'None'}",
                "Creation point allocations: "
                + (
                    ", ".join(
                        f"{code} {amount:+d}"
                        for code, amount in self._creation_allocations.items()
                        if amount
                    )
                    or "None"
                ),
                f"Outliers: {', '.join(self._selected_outlier_names()) or 'None'}",
                f"Specialization packs: {', '.join(self._selected_tile_names(self.specialization_tiles)) or 'None'}",
            )
        )
        if self.selected_mode == "Core":
            selected_equipment = self._selected_tile_names(self.equipment_tiles)
            lines.append(f"Equipment pack: {', '.join(selected_equipment) or 'None'}")
        else:
            selected_aspects = [
                value[0]["name"] for value in self._selected_light_aspects.values()
            ]
            selected_powers = [
                value["name"] for value in self._selected_light_powers.values()
            ]
            selected_supers = [
                value["name"] for value in self._selected_light_supers.values()
            ]
            lines.append(f"Light Aspects: {', '.join(selected_aspects) or 'None'}")
            lines.append(f"Light Abilities / Grenades: {', '.join(selected_powers) or 'None'}")
            lines.append(f"Supers: {', '.join(selected_supers) or 'None'}")

        character = getattr(self, "generated_character", None)
        if character is None:
            lines.extend(
                (
                    "",
                    "CALCULATED OUTPUTS",
                    "Generate a character to calculate derived values.",
                )
            )
            return "\n".join(lines)

        selected_outlier_names = self._selected_outlier_names()
        lines.extend(
            (
                "",
                "GENERATED CHARACTER",
                f"Name: {character.name}",
                f"Soldier type: {character.soldier_type or 'None'}",
                f"Rank: {character.rank or 'None'}",
                f"Background: upbringing={character.upbringing or 'None'}, "
                f"environment={character.environment or 'None'}, "
                f"lifestyle={character.lifestyle or 'None'}",
                f"Starting XP / remaining XP / XP spent: "
                f"{character.starting_experience:,} / {character.experience:,} / "
                f"{character.experience_spent:,}",
                f"Experience tier: {character.experience_tier}",
                "Characteristics: "
                + ", ".join(
                    f"{code} {value}"
                    for code, value in character.characteristics.items()
                ),
                "Mythic characteristics: "
                + (
                    ", ".join(
                        f"{code} {value}"
                        for code, value in character.mythic_characteristics.items()
                    )
                    or "None"
                ),
                f"Skills: {character.skills or 'None'}",
                f"Abilities: {', '.join(character.abilities) or 'None'}",
                f"Outliers applied: {', '.join(character.outliers) or 'None'}",
                f"Specialization packs applied: "
                f"{', '.join(character.specialization_packs) or 'None'}",
                f"Equipment: {', '.join(character.equipment) or 'None'}",
                f"Equipment pack: {character.equipment_pack or 'None'}",
                f"Armor: {character.armor or 'None'}",
                f"Weapons: {', '.join(character.weapons) or 'None'}",
                f"Connections: {', '.join(character.connections) or 'None'}",
                f"Light Aspects: {', '.join(character.light_aspects) or 'None'}",
                f"Light Abilities: {', '.join(character.light_abilities) or 'None'}",
                f"Light Grenades: {', '.join(character.light_grenades) or 'None'}",
                f"Supers: {', '.join(character.supers) or 'None'}",
                f"Wounds / fatigue / credits / Luck available / total: "
                f"{character.wounds} / {character.fatigue} / {character.credits} / "
                f"{character.luck_available} / {character.luck_total}",
                "",
                "CALCULATED OUTPUTS",
            )
        )

        modifier_rules = (
            self.game_data.get("characteristic_modifiers", "characteristic_modifiers")
            or {}
        ).get("modifier_rules", {})
        modifier_formula = modifier_rules.get("below_100", "floor(value / 10)")
        characteristic_modifiers = {
            code: value // 10
            for code, value in character.characteristics.items()
        }

        movement_document = (
            self.game_data.get("movement_speeds", "movement_speeds") or {}
        ).get("movement_speeds", {})
        movement_table = movement_document.get("table", [])
        agility_bonus = self._mythic_value(character, "AGI")
        agility_bonus += sum(
            1
            for aspect in self._selected_light_aspects.values()
            if "Agility Modifier is increased by 1 when figuring Movement Speeds."
            in aspect[0].get("description", "")
        )
        agility_modifier = characteristic_modifiers["AGI"] + agility_bonus
        movement = next(
            (
                row
                for row in movement_table
                if row.get("mod") == agility_modifier
            ),
            None,
        )
        movement_values = (
            ", ".join(
                f"{key.title()} {value} m"
                for key, value in movement.items()
                if key != "mod"
            )
            if movement
            else f"No movement table entry for modifier {agility_modifier}"
        )
        lines.append(
            f"Movement speeds (Agility Modifier {modifier_formula}; "
            f"{characteristic_modifiers['AGI']} + Mythic/Aspect {agility_bonus} = "
            f"{agility_modifier}): {movement_values}"
        )

        wounds_document = (
            self.game_data.get("wounds_formula", "wounds_formula") or {}
        ).get("wounds_formula", {})
        wounds_formula = wounds_document.get("formula", {})
        toughness_modifier = characteristic_modifiers["TOU"]
        mythic_toughness = mythic_value(character.mythic_characteristics.get("TOU", 0))
        toughness_multiplier = self._rule_multiplier(
            wounds_formula.get("toughness_modifier", "Add Toughness Modifier * 2"),
            WOUNDS_PER_TOUGHNESS_MODIFIER,
        )
        mythic_toughness_multiplier = self._rule_multiplier(
            wounds_formula.get("mythic_toughness", "Add Mythic Toughness * 2"),
            WOUNDS_PER_MYTHIC_TOUGHNESS,
        )
        robust_count = selected_outlier_names.count("Robust")
        wounds_total = max_wounds(
            character.characteristics["TOU"],
            mythic_toughness,
            robust_count,
            base=wounds_formula.get("base", WOUNDS_BASE),
            toughness_multiplier=toughness_multiplier,
            mythic_multiplier=mythic_toughness_multiplier,
        )
        lines.append(
            f"Wounds ({wounds_document.get('calculation', '40 + (Toughness Modifier × 2) + (Mythic Toughness × 2)')}): "
            f"{wounds_formula.get('base', WOUNDS_BASE)} + ({toughness_modifier} × {toughness_multiplier}) + "
            f"({mythic_toughness} × {mythic_toughness_multiplier}) + "
            f"Robust {robust_count} × {ROBUST_WOUNDS} = {wounds_total}"
        )
        lines.append(
            f"Character model Wounds value: {character.wounds}"
        )

        perception_document = (
            self.game_data.get("perceptive_range", "perceptive_range") or {}
        ).get("perceptive_range", {})
        base_formula = perception_document.get("base_formula", "perception * 2")
        base_multiplier = self._rule_multiplier(base_formula, 2)
        vigil_effect = self._outlier_record("Vigil").get("effect", "")
        vigil_bonus = (
            int(
                vigil_effect.rsplit("by", 1)[1]
                .strip()
                .split()[0]
                .rstrip(".")
            )
            if "Vigil" in selected_outlier_names
            else 0
        )
        perception_multiplier = base_multiplier + vigil_bonus
        perception = character.characteristics["PER"]
        lines.append(
            f"Perceptive range (Perception × {base_multiplier}"
            f"{f' + Vigil {vigil_bonus}' if vigil_bonus else ''}): {perception} m × "
            f"{perception_multiplier} = {perception * perception_multiplier} m"
        )

        encumbrance_document = (
            self.game_data.get("encumberance", "encumberance") or {}
        ).get("encumbrance", {})
        carry_formula = encumbrance_document.get(
            "carry_weight", "Half of Strength + Toughness"
        )
        strongman = "Strongman" in selected_outlier_names
        mythic_document = (
            self.game_data.get(
                "mythic_characteristics", "mythic_characteristics"
            )
            or {}
        ).get("mythic", {})
        strength_carry_bonus = mythic_document.get("strength", {}).get(
            "carry_weight_bonus", "X * 10"
        )
        toughness_carry_bonus = mythic_document.get("toughness", {}).get(
            "carry_weight_bonus", "X * 10"
        )
        strength_bonus_multiplier = self._rule_multiplier(
            strength_carry_bonus, 10
        )
        toughness_bonus_multiplier = self._rule_multiplier(
            toughness_carry_bonus, 10
        )
        spartan = any(
            trait.get("name") == "Carry Weight"
            and "Doubles Strength and Toughness" in trait.get("effect", "")
            for trait in (
                self.game_data.get("soldier_type", character.soldier_type) or {}
            ).get("traits", [])
        )
        strength_value = (
            character.characteristics["STR"]
            + self._mythic_value(character, "STR") * strength_bonus_multiplier
        )
        toughness_value = (
            character.characteristics["TOU"]
            + self._mythic_value(character, "TOU") * toughness_bonus_multiplier
        )
        if spartan:
            strength_value *= 2
            toughness_value *= 2
        carry_weight = (
            strength_value + toughness_value
            if strongman
            else (strength_value + toughness_value) / 2
        )
        lines.append(
            f"Carry weight ({carry_formula}; Mythic bonuses "
            f"STR {strength_carry_bonus}, TOU {toughness_carry_bonus}"
            f"{'; Spartan doubling' if spartan else ''}"
            f"{'; Strongman removes halving' if strongman else ''}): "
            f"({strength_value:g} + {toughness_value:g})"
            f"{'' if strongman else ' / 2'} = {carry_weight:g}"
        )
        lift_formula = encumbrance_document.get("lift_weight", "Carry Weight * 3")
        push_formula = encumbrance_document.get("push_weight", "Carry Weight * 5")
        lift_weight = carry_weight * self._rule_multiplier(lift_formula, 3)
        push_weight = carry_weight * self._rule_multiplier(push_formula, 5)
        lines.append(
            f"Lift weight ({lift_formula}): "
            f"{lift_weight:g}"
        )
        lines.append(
            f"Push weight ({push_formula}): "
            f"{push_weight:g}"
        )

        lines.extend(("", "GENERATOR LOG", *character.debug_log))
        return "\n".join(lines)

    @property
    def selected_mode(self):
        return self.version_and_expansions_page.selected_mode

    def _refresh_initial_setup_options(self):
        if not hasattr(self, "game_data"):
            return

        page = self.initial_character_setup_page
        if self.selected_mode == "Light & Sky":
            categories = (
                ("human", "Human Soldier Type"),
                ("guardian", "Guardian Soldier Type"),
                ("subclass", "Subclass"),
                ("connection", "Connection"),
            )
            option_combos = {
                "human": self.human_combo,
                "guardian": self.guardian_combo,
                "subclass": self.subclass_combo,
                "connection": self.connection_combo,
            }
        else:
            categories = (
                ("soldier", "Soldier Type"),
                ("upbringing", "Upbringing"),
                ("environment", "Environment"),
                ("lifestyles", "Lifestyles"),
            )
            option_combos = {
                "soldier": self.soldier_combo,
                "upbringing": self.upbringing_combo,
                "environment": self.environment_combo,
                "lifestyles": self.lifestyle_combos[0],
            }

        page.set_categories(categories)
        for category, label in categories:
            combo = option_combos[category]
            combos = self.lifestyle_combos if category == "lifestyles" else (combo,)
            options = []
            selected_values = []
            for option_combo in combos:
                for index in range(option_combo.count()):
                    value = option_combo.itemData(index)
                    if value is None:
                        value = option_combo.itemText(index)
                    if not value:
                        continue
                    if not any(
                        existing_value == value
                        for _, existing_value, _ in options
                    ):
                        options.append(
                            (
                                option_combo.itemText(index),
                                value,
                                self._format_initial_setup_option(
                                    category, value
                                ),
                            )
                        )
                value = option_combo.currentData()
                if value is None:
                    value = option_combo.currentText()
                if value:
                    selected_values.append(value)
            page.set_category_options(
                category,
                label,
                options,
                selected_values,
            )

    def _format_initial_setup_option(self, category, value):
        record = None
        if category in {"soldier", "human", "guardian"}:
            record = self.game_data.get("soldier_type", value)
        elif category in {"upbringing", "environment", "lifestyles"}:
            family = "lifestyle" if category == "lifestyles" else category
            document = self.game_data.get(family, family) or {}
            record = next(
                (
                    item
                    for item in document.get(family, [])
                    if item.get("name") == value
                ),
                None,
            )
        elif category == "subclass":
            guardian = self.game_data.get(
                "soldier_type", self.guardian_combo.currentData()
            ) or {}
            record = guardian.get("subclasses", {}).get(value)
        elif category == "connection":
            document = self.game_data.get("connections", "connections") or {}
            connections = document.get("connections", document)
            record = next(
                (
                    connection
                    for group in ("light", "darkness", "specialized")
                    for connection in connections.get(group, [])
                    if connection.get("name") == value
                ),
                None,
            )

        if not record:
            return "No additional details."

        sections = []
        if record.get("experience_cost") is not None:
            sections.append(f"Experience Cost: {record['experience_cost']:,} XP")
        for key, heading in (
            ("base_characteristics", "Base Characteristics"),
            ("mythic_characteristics", "Mythic Characteristics"),
            ("advancements", "Advancements"),
            ("characteristic_modifiers", "Characteristic Modifiers"),
        ):
            values = record.get(key)
            if isinstance(values, dict):
                entries = [
                    f"{code}: {amount}"
                    for code, amount in values.items()
                    if amount is not None
                ]
                if entries:
                    sections.append(f"{heading}: {', '.join(entries)}")

        traits = record.get("traits", [])
        if traits:
            trait_details = []
            for trait in traits:
                if isinstance(trait, dict):
                    name = trait.get("name", "Trait")
                    effect = trait.get("effect")
                    trait_details.append(
                        f"{name}: {effect}" if effect else name
                    )
                else:
                    trait_details.append(str(trait))
            sections.append("Traits: " + "; ".join(trait_details))

        for key, heading in (("bonuses", "Bonuses"), ("penalties", "Penalties")):
            values = record.get(key, [])
            if values:
                sections.append(f"{heading}: {', '.join(map(str, values))}")

        if category == "lifestyles":
            for outcome in record.get("outcomes", []):
                outcome_details = [f"Roll {outcome.get('roll', '?')}"]
                for key, heading in (
                    ("bonuses", "Bonuses"),
                    ("penalties", "Penalties"),
                ):
                    values = outcome.get(key, [])
                    if values:
                        outcome_details.append(
                            f"{heading}: {', '.join(map(str, values))}"
                        )
                sections.append(" | ".join(outcome_details))

        if record.get("information"):
            sections.append(f"Information: {record['information']}")
        if record.get("training"):
            sections.append(f"Training: {', '.join(record['training'])}")

        return "\n".join(sections) if sections else "No additional details."

    def select_initial_setup_option(self, category, value, checked):
        if checked and category in {"soldier", "human", "guardian"}:
            soldier_data = self.game_data.get("soldier_type", value) or {}
            try:
                requirements = self._skill_training_requirements(soldier_data)
                if requirements:
                    skill_count, training_bonus = requirements
                    skills_document = self.game_data.get("skills", "skills") or {}
                    skill_names = [
                        skill.get("name")
                        for skill in skills_document.get("skills", [])
                        if skill.get("name")
                    ]
                    previous_selection = self._selected_soldier_skills.get(
                        value, {}
                    )
                    dialog = SkillTrainingDialog(
                        skill_names,
                        skill_count,
                        training_bonus,
                        selected_skills=previous_selection,
                        parent=self,
                    )
                    if dialog.exec() != QDialog.DialogCode.Accepted:
                        self._refresh_initial_setup_options()
                        return
                    self._selected_soldier_skills[value] = {
                        skill: training_bonus
                        for skill in dialog.selected_skills
                    }
            except ValueError as error:
                QMessageBox.warning(
                    self,
                    "Skill Training Selection",
                    str(error),
                )
                self._refresh_initial_setup_options()
                return

        if category == "lifestyles":
            if checked:
                matching_combo = next(
                    (combo for combo in self.lifestyle_combos if not combo.currentData()),
                    None,
                )
                if matching_combo is None:
                    self._refresh_initial_setup_options()
                    return
                index = matching_combo.findData(value)
            else:
                matching_combo = next(
                    (
                        combo
                        for combo in reversed(self.lifestyle_combos)
                        if (combo.currentData() or combo.currentText()) == value
                    ),
                    None,
                )
                if matching_combo is None:
                    return
                index = 0
        else:
            combo = {
                "soldier": self.soldier_combo,
                "human": self.human_combo,
                "guardian": self.guardian_combo,
                "upbringing": self.upbringing_combo,
                "environment": self.environment_combo,
                "subclass": self.subclass_combo,
                "connection": self.connection_combo,
            }[category]
            index = combo.findData(value)
            if index < 0:
                index = combo.findText(value)
        if index >= 0:
            if category == "lifestyles":
                matching_combo.setCurrentIndex(index)
            else:
                combo.setCurrentIndex(index)
        self._refresh_initial_setup_options()

    @staticmethod
    def _skill_training_requirements(soldier_data):
        skill_trait = next(
            (
                trait
                for trait in soldier_data.get("traits", [])
                if isinstance(trait, dict)
                and isinstance(trait.get("name"), str)
                and trait["name"].casefold() == "skill training"
            ),
            None,
        )
        if skill_trait is None:
            return None

        effect = skill_trait.get("effect")
        if not isinstance(effect, str):
            raise ValueError("The Skill Training trait is missing its effect text.")

        number_words = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
        }
        count_match = re.search(
            r"\b(\d+|one|two|three|four|five|six|seven|eight|nine|ten)"
            r"\s+skills?\b",
            effect,
            re.IGNORECASE,
        )
        level_match = re.search(
            r"\bat\s+(Trained|\+\d+)\b",
            effect,
            re.IGNORECASE,
        )
        if not count_match or not level_match:
            raise ValueError(
                "The Skill Training trait must specify a skill count and training level."
            )

        count_text = count_match.group(1).casefold()
        skill_count = number_words.get(count_text)
        if skill_count is None:
            skill_count = int(count_text)
        level_text = level_match.group(1)
        training_bonus = (
            0 if level_text.casefold() == "trained" else int(level_text[1:])
        )
        if (
            skill_count < 1
            or training_bonus < 0
            or training_bonus > 20
            or training_bonus % 10
        ):
            raise ValueError(
                "The Skill Training trait specifies an unsupported count or training level."
            )
        return skill_count, training_bonus

    def _build_specialization_pack_tiles(self):
        while self.specialization_grid.count():
            item = self.specialization_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.specialization_tiles.clear()
        document = self.game_data.get(
            "specialization_packs", "specialization_packs"
        ) if hasattr(self, "game_data") else None
        if not document:
            self.update_specialization_selection()
            return
        ability_document = self.game_data.get("light_abilities", "abilities") or {}
        ability_descriptions = {
            item.get("name", "").casefold(): item.get("description", "")
            for item in ability_document.get("abilities", [])
        }
        skill_document = self.game_data.get("skills", "skills") or {}
        skill_descriptions = {
            item.get("name", "").casefold(): item.get("description", "")
            for item in skill_document.get("skills", [])
        }

        row = 0
        for section_name, packs in (
            ("STANDARD PACKS", document.get("specialization_packs", {}).get("standard", [])),
            ("LIMITED PACKS", document.get("specialization_packs", {}).get("limited", [])),
        ):
            if not packs:
                continue

            section_label = QLabel(section_name)
            section_label.setStyleSheet(
                "color: #f2f0e6; font-weight: bold; font-size: 14px;"
            )
            self.specialization_grid.addWidget(section_label, row, 0, 1, 3)
            row += 1

            for index, pack in enumerate(packs):
                column = index % 3
                tile_row = row + index // 3
                tile = QFrame(self.specialization_content)
                tile.setStyleSheet(
                    "QFrame { background-color: #242424; "
                    "border: 2px solid #526b28; border-radius: 8px; }"
                )
                tile.setMinimumHeight(145)
                tile.setMaximumHeight(145)
                tile_layout = QVBoxLayout(tile)
                tile_layout.setContentsMargins(5, 5, 5, 5)
                tile_layout.setSpacing(4)
                pack_button = QPushButton(pack["name"])
                pack_button.setCheckable(True)
                pack_button.setMinimumHeight(48)
                pack_button.setStyleSheet(
                    "QPushButton {"
                    " text-align: left;"
                    " background-color: #526b28;"
                    " color: #ffffff;"
                    " border: 2px solid #788f3e;"
                    " border-radius: 6px;"
                    " padding: 8px 12px;"
                    " font-size: 16px;"
                    " font-weight: bold;"
                    "}"
                    "QPushButton:hover {"
                    " background-color: #788f3e;"
                    " border-color: #f7d36b;"
                    "}"
                    "QPushButton:checked {"
                    " background-color: #35451d;"
                    " border: 3px solid #f7d36b;"
                    "}"
                    "QPushButton:pressed {"
                    " background-color: #35451d;"
                    " border-color: #f7d36b;"
                    "}"
                )
                tile_layout.addWidget(pack_button)
                table_widget = QWidget(tile)
                table_widget.setStyleSheet("border: none;")
                table_layout = QGridLayout(table_widget)
                table_layout.setContentsMargins(0, 0, 0, 0)
                table_layout.setHorizontalSpacing(0)
                table_layout.setVerticalSpacing(1)
                table_layout.setColumnStretch(0, 1)
                table_layout.setColumnStretch(1, 1)
                tile_layout.addWidget(table_widget)

                header_style = (
                    "color: #ffffff; background-color: #526b28; "
                    "font-weight: bold; padding: 3px;"
                )
                ability_header = QLabel("ABILITY")
                ability_header.setStyleSheet(header_style)
                skill_header = QLabel("SKILL")
                skill_header.setStyleSheet(header_style)
                table_layout.addWidget(ability_header, 0, 0)
                table_layout.addWidget(skill_header, 0, 1)

                for index, (ability, skill) in enumerate(
                    zip(pack.get("abilities", []), pack.get("skills", [])),
                    start=1,
                ):
                    ability_label = DelayedTooltipLabel(
                        ability,
                        ability_descriptions.get(ability.casefold(), ""),
                    )
                    skill_name = skill.partition(" (")[0]
                    skill_key = skill_name.casefold()
                    skill_description = skill_descriptions.get(skill_key, "")
                    if not skill_description and skill_key.endswith("s"):
                        skill_description = skill_descriptions.get(skill_key[:-1], "")
                    skill_label = DelayedTooltipLabel(
                        skill,
                        skill_description,
                    )
                    table_layout.addWidget(ability_label, index, 0)
                    table_layout.addWidget(skill_label, index, 1)

                pack_button.toggled.connect(
                    lambda checked, selected_button=pack_button:
                    self.select_specialization_tile(selected_button, checked)
                )
                pack_button.toggled.connect(
                    lambda checked, card=tile: card.setStyleSheet(
                        "QFrame { background-color: #242424; "
                        + (
                            "border: 3px solid #f7d36b;"
                            if checked
                            else "border: 2px solid #526b28;"
                        )
                        + " border-radius: 8px; }"
                    )
                )
                self.specialization_tiles.append((pack_button, pack["name"]))
                self.specialization_grid.addWidget(tile, tile_row, column)

            row += (len(packs) + 2) // 3 + 1
        self.update_specialization_selection()

    def select_specialization_tile(self, selected_button, checked):
        if checked:
            for button, _ in self.specialization_tiles:
                if button is not selected_button:
                    button.setChecked(False)
        self.update_specialization_selection()

    def update_specialization_selection(self):
        if self.selected_mode == "Light & Sky":
            button_text = "Next: Light Abilities / Light Aspects"
        else:
            button_text = "Next: Equipment Packs"
        self.specialization_done_button.setText(button_text)
        has_selection = any(
            button.isChecked() for button, _ in self.specialization_tiles
        )
        self.specialization_done_button.setEnabled(has_selection)
        self.character_setup_home.set_specialization_selected(has_selection)

    def open_specialization_page(self):
        self.update_specialization_selection()
        self.pages.setCurrentWidget(self.specialization_page)

    def finish_specialization_selection(self):
        if hasattr(self, "generated_character"):
            if not hasattr(self, "_pre_specialization_skills"):
                self._pre_specialization_skills = self.generated_character.skills.copy()
                self._pre_specialization_abilities = self.generated_character.abilities.copy()
            else:
                self.generated_character.skills = self._pre_specialization_skills.copy()
                self.generated_character.abilities = self._pre_specialization_abilities.copy()

            selected_names = [
                name for button, name in self.specialization_tiles if button.isChecked()
            ]
            document = self.game_data.get(
                "specialization_packs", "specialization_packs"
            ) or {}
            pack_sections = document.get("specialization_packs", {})
            selected_packs = [
                pack
                for section in ("standard", "limited")
                for pack in pack_sections.get(section, [])
                if pack["name"] in selected_names
            ]
            self.generated_character.specialization_packs = []
            for pack in selected_packs:
                self.generated_character.apply_specialization_pack(pack)
        self.open_equipment_page()

    def _build_outlier_tiles(self):
        while self.outlier_grid.count():
            item = self.outlier_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.outlier_tiles.clear()
        documents = [("CORE", "outliers", 1)]
        if self.selected_mode == "Light & Sky":
            documents.append(("LIGHT & SKY", "light_and_sky_outliers", 2))

        row = 0
        for section_name, document_name, luck_cost in documents:
            document = self.game_data.get("outliers", document_name) or {}
            outliers = document.get("outliers", {}).get("list", [])
            if not outliers:
                continue

            section_label = QLabel(f"{section_name} OUTLIERS (BURN {luck_cost} LUCK EACH)")
            section_label.setStyleSheet(
                "color: #f2f0e6; font-weight: bold; font-size: 14px;"
            )
            self.outlier_grid.addWidget(section_label, row, 0, 1, 3)
            row += 1

            for index, outlier in enumerate(outliers):
                card, select_button = self._create_selection_tile(
                    outlier["name"],
                    outlier["effect"],
                    min_height=125,
                    parent=self.outlier_content,
                )
                select_button.toggled.connect(
                    lambda checked, button=select_button, selected_outlier=outlier:
                    self._handle_outlier_selection(
                        button, selected_outlier, checked
                    )
                )
                self.outlier_tiles.append((select_button, outlier, luck_cost))
                self.outlier_grid.addWidget(card, row + index // 3, index % 3)

            row += (len(outliers) + 2) // 3 + 1
        self.update_outlier_selection()

    def _handle_outlier_selection(self, button, outlier, checked):
        outlier_name = outlier.get("name")
        if checked and outlier_name in {"Aptitude", "Forte"}:
            if not hasattr(self, "generated_character"):
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            if outlier_name == "Aptitude":
                characteristic_document = (
                    self.game_data.get("characteristics", "characteristics") or {}
                )
                characteristics = characteristic_document.get(
                    "characteristics", []
                )
                options = [
                    (item["name"], item["id"].upper())
                    for item in characteristics
                    if isinstance(item.get("id"), str)
                    and item["id"].upper() in CHAR_CODES
                    and item.get("name")
                ]
                prompt = "Choose a characteristic to increase by +5:"
            else:
                mythic_names = {
                    "STR": "Strength",
                    "TOU": "Toughness",
                    "AGI": "Agility",
                }
                options = [
                    (mythic_names[code], code)
                    for code in MYTHIC_CHAR_CODES
                ]
                prompt = "Choose a Mythic Characteristic to increase by +1:"

            if not options:
                QMessageBox.warning(
                    self,
                    f"{outlier_name} Selection Unavailable",
                    "No eligible characteristics are available to choose.",
                )
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            previous_choice = self._outlier_characteristics.get(outlier_name)
            current_index = next(
                (
                    index
                    for index, (_, code) in enumerate(options)
                    if code == previous_choice
                ),
                0,
            )
            labels = [label for label, _ in options]
            label, accepted = QInputDialog.getItem(
                self,
                f"{outlier_name} Selection",
                prompt,
                labels,
                current_index,
                False,
            )
            if not accepted:
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            selected_code = next(
                code for option_label, code in options if option_label == label
            )
            self._outlier_characteristics[outlier_name] = selected_code
        self.update_outlier_selection()

    def update_outlier_selection(self):
        selected_count = sum(tile.isChecked() for tile, _, _ in self.outlier_tiles)
        luck_cost = sum(cost for tile, _, cost in self.outlier_tiles if tile.isChecked())
        luck_total = self._starting_luck - luck_cost
        self.outlier_page.available_luck_label.setText(
            f"Luck available: {self._starting_luck} / Total: {luck_total}"
        )
        for select_button, _, cost in self.outlier_tiles:
            select_button.setEnabled(select_button.isChecked() or cost <= luck_total)
        self.outlier_done_button.setText(
            f"Next: Specialization Packs ({selected_count}; Burn {luck_cost} Luck)"
        )

    def finish_outlier_selection(self):
        if hasattr(self, "generated_character"):
            self.generated_character.outliers = []
            self.generated_character.luck_available = self._starting_luck
            self.generated_character.luck_total = self._starting_luck
            self.generated_character.characteristics = (
                self._pre_outlier_characteristics.copy()
            )
            self.generated_character.mythic_characteristics = (
                self._pre_outlier_mythic_characteristics.copy()
            )
            for tile, outlier, luck_cost in self.outlier_tiles:
                if tile.isChecked():
                    self.generated_character.apply_outlier(
                        outlier,
                        luck_cost,
                        characteristic=self._outlier_characteristics.get(
                            outlier.get("name")
                        ),
                    )
        self.open_specialization_page()

    def _build_equipment_tiles(self):
        self.equipment_page.set_light_mode(False)
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.equipment_tiles.clear()
        if self.selected_mode != "Core" or not hasattr(self, "game_data"):
            return

        soldier_name = getattr(self, "_selected_core_soldier", None)
        if not soldier_name:
            return
        soldier_data = self.game_data.get("soldier_type", soldier_name) or {}
        equipment_sets = soldier_data.get("equipment_sets", {})
        if not equipment_sets:
            self.equipment_grid.addWidget(
                QLabel("No equipment packs are available for this soldier type."),
                0, 0, 1, 3,
            )
            return

        for index, (pack_name, items) in enumerate(equipment_sets.items()):
            tile, select_button = self._create_selection_tile(
                pack_name.replace("_", " ").title(),
                "\n".join(items),
                min_height=145,
            )
            select_button.toggled.connect(
                lambda checked, selected_tile=select_button: self.select_equipment_tile(
                    selected_tile, checked
                )
            )
            self.equipment_tiles.append((select_button, pack_name, items))
            self.equipment_grid.addWidget(tile, index // 3, index % 3)

    def select_equipment_tile(self, selected_tile, checked):
        if checked:
            for button, _, _ in self.equipment_tiles:
                if button is not selected_tile:
                    button.setChecked(False)
        self.update_equipment_selection()

    def update_equipment_selection(self):
        selected = next(
            (pack_name for button, pack_name, _ in self.equipment_tiles if button.isChecked()),
            None,
        )
        self.equipment_done_button.setText(
            f"Done ({selected.replace('_', ' ').title()})" if selected else "Done"
        )

    def open_equipment_page(self):
        self.character_setup_home.set_character_ready_to_export(False)
        if self.selected_mode == "Light & Sky":
            self.equipment_page.set_light_mode(True)
            self._build_light_power_tiles()
            self.update_light_power_selection()
        else:
            self._build_equipment_tiles()
            self.update_equipment_selection()
        self.pages.setCurrentWidget(self.equipment_page)

    def finish_equipment_selection(self):
        if self.selected_mode == "Light & Sky":
            self.finish_light_power_selection()
            return

        if hasattr(self, "generated_character"):
            selected = next(
                (
                    (pack_name, items)
                    for tile, pack_name, items in self.equipment_tiles
                    if tile.isChecked()
                ),
                None,
            )
            self.generated_character.equipment = []
            self.generated_character.equipment_pack = None
            if selected:
                self.generated_character.apply_equipment_pack(*selected)
        self.character_setup_home.set_character_ready_to_export(True)
        self.pages.setCurrentWidget(self.character_setup_home)

    def _clear_equipment_grid(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def select_light_category(self, category):
        self._selected_light_category = category
        self._build_light_power_tiles()

    def _build_light_power_tiles(self):
        self._clear_equipment_grid()
        self.equipment_tiles.clear()
        self.light_aspect_tiles.clear()
        self.light_ability_tiles.clear()
        self.equipment_page.set_light_mode(True)
        self.equipment_page_title.setText("LIGHT ASPECTS AND ABILITIES")

        aspects_document = self.game_data.get("light_aspects", "light_aspects") or {}
        aspects_by_connection = aspects_document.get("light_aspects", {})
        selected_connection = self.connection_combo.currentText()
        selected_connection_group = self._connection_group(selected_connection)
        selected_class = self.guardian_combo.currentData() or ""
        ability_document = self.game_data.get(
            "light_abilities", "light_abilities_and_grenades"
        ) or {}
        abilities = ability_document.get("abilities", [])
        grenades = ability_document.get("grenades", [])
        ability_rules = self.game_data.get(
            "light_ability_rules", "light_ability_rules"
        ) or {}
        light_ability_rules = ability_rules.get("light_abilities", {})
        super_rules = light_ability_rules["supers"]
        grenade_super_rule = light_ability_rules["grenade_supers"]["rule"]

        all_aspects = [
            (connection.title(), aspect)
            for connection, records in aspects_by_connection.items()
            if isinstance(records, list)
            for aspect in records
            if self._matches_selected_connection(
                aspect,
                selected_connection,
                selected_connection_group,
                fallback_connection=connection,
            )
        ]

        available_powers = [
            (ability, "Light Ability")
            for ability in abilities
            if self._matches_selected_connection(
                ability, selected_connection, selected_connection_group
            )
            and (
                str(ability.get("class", "")).strip().casefold() == "all"
                or str(ability.get("class", "")).strip().casefold()
                == str(selected_class).strip().casefold()
            )
        ]
        available_powers.extend(
            (grenade, "Light Grenade")
            for grenade in grenades
            if self._matches_selected_connection(
                grenade, selected_connection, selected_connection_group
            )
        )

        valid_aspect_keys = {
            (connection.casefold(), aspect["name"].casefold())
            for connection, aspect in all_aspects
        }
        valid_power_keys = {
            (power_type, power["name"].casefold())
            for power, power_type in available_powers
        }
        self._selected_light_aspects = {
            key: value
            for key, value in self._selected_light_aspects.items()
            if key in valid_aspect_keys
        }
        self._selected_light_powers = {
            key: value
            for key, value in self._selected_light_powers.items()
            if key in valid_power_keys
        }
        self._selected_light_supers = {
            key: value
            for key, value in self._selected_light_supers.items()
            if key in valid_power_keys
        }

        if self._selected_light_category == "aspects":
            self.equipment_page.options_title.setText("Light Aspects")
            self.equipment_page.options_description.setText(
                "Select one Light Aspect."
            )
            for index, (connection, aspect) in enumerate(all_aspects):
                key = (connection.casefold(), aspect["name"].casefold())
                tile, select_button = self._create_selection_tile(
                    aspect["name"],
                    f"{connection} | XP {self._light_aspect_cost(aspect, connection)}\n"
                    f"{aspect['description']}",
                    min_height=145,
                )
                select_button.toggled.connect(
                    lambda checked, selected_tile=select_button, selected_key=key,
                    selected_aspect=aspect, selected_connection_name=connection:
                    self._select_light_tile(
                        selected_tile,
                        "aspect",
                        checked,
                        selected_key,
                        (selected_aspect, selected_connection_name),
                    )
                )
                self.light_aspect_tiles.append(
                    (select_button, aspect, connection)
                )
                select_button.setChecked(key in self._selected_light_aspects)
                self.equipment_grid.addWidget(tile, index // 3, index % 3)
        elif self._selected_light_category == "powers":
            self.equipment_page.options_title.setText("Light Abilities / Grenades")
            self.equipment_page.options_description.setText(
                "Select up to two Light Abilities and/or Light Grenades."
            )
            power_selection = self._selected_light_powers
        elif self._selected_light_category == "supers":
            self.equipment_page.options_title.setText("Supers")
            self.equipment_page.options_description.setText(
                "Select one Super. Cost: "
                f"{super_rules['experience_cost_multiplier']:g}x XP and "
                f"{super_rules['energy_cost_multiplier']:g}x Energy."
            )
            power_selection = self._selected_light_supers
        else:
            power_selection = None

        if self._selected_light_category in {"powers", "supers"}:
            for index, (power, power_type) in enumerate(available_powers):
                description = power.get("description") or power.get("special_rules", "")
                is_super = self._selected_light_category == "supers"
                experience_cost = (
                    self._super_experience_cost(
                        power, super_rules["experience_cost_multiplier"]
                    )
                    if is_super
                    else int(power.get("experience_cost", 0) or 0)
                )
                energy_cost = power.get("light_cost", "N/A")
                if is_super:
                    energy_cost = self._super_energy_cost(
                        energy_cost, super_rules["energy_cost_multiplier"]
                    )
                    tile_details = (
                        f"{power_type} Super | XP {experience_cost} | "
                        f"Super Energy {energy_cost}"
                    )
                else:
                    tile_details = (
                        f"{power_type} | XP {experience_cost} | "
                        f"Light {energy_cost}"
                    )
                if power_type == "Light Grenade":
                    damage_parts = [
                        str(power[field])
                        for field in ("damage_roll", "base_damage")
                        if power.get(field) is not None
                    ]
                    damage = " + ".join(damage_parts) if damage_parts else "None"
                    tile_details += (
                        f"\nDamage: {damage} | Range: {power.get('range') or 'N/A'}"
                    )
                    if is_super:
                        tile_details += f"\nSuper effect: {grenade_super_rule}"
                if is_super:
                    super_description = power.get("super_description") or (
                        grenade_super_rule
                        if power_type == "Light Grenade"
                        else "No Super description is specified in the data."
                    )
                    tile_details += (
                        f"\nRegular description: {description}"
                        f"\nSuper description: {super_description}"
                    )
                else:
                    tile_details += f"\n{description}"
                power_data = dict(power)
                if is_super:
                    power_data["experience_cost"] = experience_cost
                    power_data["super_energy_cost"] = energy_cost
                    power_data["super_description"] = super_description
                    power_data["_power_type"] = (
                        "Super Grenade"
                        if power_type == "Light Grenade"
                        else "Super Ability"
                    )
                else:
                    power_data["description"] = description
                    power_data["_power_type"] = power_type
                key = (power_type, power["name"].casefold())
                tile, select_button = self._create_selection_tile(
                    power["name"],
                    tile_details,
                    min_height=145,
                )
                select_button.toggled.connect(
                    lambda checked, selected_tile=select_button,
                    selected_key=key, selected_power=power_data:
                    self._select_light_tile(
                        selected_tile,
                        "super" if is_super else "power",
                        checked,
                        selected_key,
                        selected_power,
                    )
                )
                self.light_ability_tiles.append((select_button, power_data))
                select_button.setChecked(key in power_selection)
                self.equipment_grid.addWidget(tile, index // 3, index % 3)
        elif self._selected_light_category not in {"aspects", "powers", "supers"}:
            self.equipment_page.options_title.setText("Select a category")
            self.equipment_page.options_description.setText(
                "Choose Light Aspects, Light Abilities / Grenades, or Supers to view options."
            )
        self.update_light_power_selection()

    def _create_selection_tile(self, title, text, min_height=125, parent=None):
        card_parent = parent if parent is not None else self.equipment_content
        card = QFrame(card_parent)
        card.setMinimumHeight(min_height)
        card.setStyleSheet(
            "QFrame { background-color: #242424; "
            "border: 2px solid #526b28; border-radius: 8px; }"
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        select_button = QPushButton(title, card)
        select_button.setCheckable(True)
        select_button.setMinimumSize(260, 72)
        select_button.setStyleSheet(
            "QPushButton {"
            " text-align: left;"
            " background-color: #526b28;"
            " color: #ffffff;"
            " border: 2px solid #788f3e;"
            " border-radius: 6px;"
            " padding: 14px;"
            " font-size: 16px;"
            " font-weight: bold;"
            "}"
            "QPushButton:hover {"
            " background-color: #788f3e;"
            " border-color: #f7d36b;"
            "}"
            "QPushButton:checked {"
            " background-color: #35451d;"
            " border: 3px solid #f7d36b;"
            "}"
            "QPushButton:pressed {"
            " background-color: #35451d;"
            " border-color: #f7d36b;"
            "}"
        )
        layout.addWidget(select_button)

        details_label = QLabel(text, card)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            "color: #d5d2c6; border: none; padding: 4px 8px 8px 8px;"
        )
        layout.addWidget(details_label)

        select_button.toggled.connect(
            lambda checked, selected_card=card: selected_card.setStyleSheet(
                "QFrame { background-color: #242424; "
                + (
                    "border: 3px solid #f7d36b;"
                    if checked
                    else "border: 2px solid #526b28;"
                )
                + " border-radius: 8px; }"
            )
        )
        return card, select_button

    def _select_light_tile(
        self, selected_tile, selection_kind, checked, selection_key, selected_value
    ):
        selections = (
            self._selected_light_aspects
            if selection_kind == "aspect"
            else (
                self._selected_light_supers
                if selection_kind == "super"
                else self._selected_light_powers
            )
        )
        limit = 1 if selection_kind in {"aspect", "super"} else 2
        if (
            checked
            and selection_key not in selections
            and len(selections) >= limit
        ):
            selected_tile.blockSignals(True)
            selected_tile.setChecked(False)
            selected_tile.blockSignals(False)
        elif checked:
            selections[selection_key] = selected_value
            if self._selected_light_xp_cost() > self._light_xp_budget():
                selections.pop(selection_key, None)
                selected_tile.blockSignals(True)
                selected_tile.setChecked(False)
                selected_tile.blockSignals(False)
        else:
            selections.pop(selection_key, None)
        self._update_light_xp_display()
        self.update_light_power_selection()

    def update_light_power_selection(self):
        aspect_count = len(self._selected_light_aspects)
        ability_count = len(self._selected_light_powers)
        super_count = len(self._selected_light_supers)
        self._update_light_xp_display()
        self.equipment_done_button.setText(
            f"Done (Aspects {aspect_count}/1; Light Powers {ability_count}/2; "
            f"Supers {super_count}/1)"
        )

    def finish_light_power_selection(self):
        if hasattr(self, "generated_character"):
            aspects = [
                aspect_and_connection[0]
                for aspect_and_connection in self._selected_light_aspects.values()
            ]
            abilities = list(self._selected_light_powers.values())
            supers = list(self._selected_light_supers.values())
            self.generated_character.apply_light_powers(aspects, abilities, supers)
            current_budget = (
                self.generated_character.experience + self._light_xp_spent
            )
            new_xp_spent = self._selected_light_xp_cost()
            self.generated_character.experience = current_budget - new_xp_spent
            self.generated_character.experience_spent += (
                new_xp_spent - self._light_xp_spent
            )
            self._light_xp_spent = new_xp_spent
        self.character_setup_home.set_character_ready_to_export(True)
        self.pages.setCurrentWidget(self.character_setup_home)

    def _light_aspect_cost(self, aspect, connection):
        selected_connection = self.connection_combo.currentText()
        cost = aspect.get("experience_cost", 0)
        return (
            cost
            if connection.strip().casefold() == selected_connection.strip().casefold()
            else cost * 2
        )

    def _light_power_xp_cost(self, power):
        return int(power.get("experience_cost", 0) or 0)

    @staticmethod
    def _super_experience_cost(power, multiplier):
        return int(power.get("experience_cost", 0) * multiplier)

    @staticmethod
    def _super_energy_cost(light_cost, multiplier):
        if isinstance(light_cost, (int, float)):
            return light_cost * multiplier
        return f"{multiplier} x {light_cost}"

    def _selected_light_xp_cost(self):
        aspect_cost = sum(
            self._light_aspect_cost(aspect, connection)
            for aspect, connection in self._selected_light_aspects.values()
        )
        power_cost = sum(
            self._light_power_xp_cost(power)
            for power in self._selected_light_powers.values()
        )
        super_cost = sum(
            self._light_power_xp_cost(power)
            for power in self._selected_light_supers.values()
        )
        return aspect_cost + power_cost + super_cost

    def _light_xp_budget(self):
        if hasattr(self, "generated_character"):
            return self.generated_character.experience + self._light_xp_spent
        return self.experience_input.value()

    def _update_light_xp_display(self):
        available_xp = self._light_xp_budget()
        spent_xp = self._selected_light_xp_cost()
        self.equipment_page.experience_remaining_label.setText(
            f"XP remaining: {available_xp - spent_xp:,} / {available_xp:,}"
        )

        xp_left = available_xp - spent_xp
        for button, aspect, connection in self.light_aspect_tiles:
            cost = self._light_aspect_cost(aspect, connection)
            button.setEnabled(button.isChecked() or cost <= xp_left)
        for button, power in self.light_ability_tiles:
            cost = self._light_power_xp_cost(power)
            button.setEnabled(button.isChecked() or cost <= xp_left)

    def _connection_group(self, selected_connection):
        selected = selected_connection.strip().casefold()
        connections_document = self.game_data.get("connections", "connections") or {}
        connections = connections_document.get("connections", connections_document)
        for group in ("light", "darkness", "specialized"):
            for connection in connections.get(group, []):
                if connection.get("name", "").strip().casefold() == selected:
                    return group
        return ""

    @staticmethod
    def _matches_selected_connection(
        record,
        selected_connection,
        selected_connection_group="",
        fallback_connection=None,
    ):
        selected = selected_connection.strip().casefold()
        selected_group = selected_connection_group.strip().casefold()
        connection_values = [record.get("connection")]
        group_values = [record.get("group")]
        if fallback_connection is not None:
            connection_values.append(fallback_connection)

        for value in connection_values + group_values:
            if isinstance(value, str):
                values = (value,)
            elif isinstance(value, (list, tuple, set)):
                values = value
            else:
                continue
            for candidate in values:
                if not isinstance(candidate, str):
                    continue
                normalized = candidate.strip().casefold()
                if normalized == "universal" or (
                    (selected and normalized == selected)
                    or (selected_group and normalized == selected_group)
                ):
                    return True
        return False

    def reset_creation_points(self):
        if not hasattr(self, "generated_character"):
            return

        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self.generated_character.characteristics = self._generated_characteristics.copy()
        self._update_creation_point_display()

    def adjust_creation_points(self, code, amount):
        if not hasattr(self, "generated_character"):
            return

        current = self._creation_allocations[code]
        total_points = self.creation_points_combo.currentData()
        spent = sum(self._creation_allocations.values())

        if amount > 0 and (spent >= total_points or current >= self._max_creation_points):
            return
        if amount < 0 and current <= 0:
            return

        self._creation_allocations[code] = current + amount
        self.generated_character.characteristics[code] += amount
        self._update_creation_point_display()

    def _update_creation_point_display(self):
        spent = sum(self._creation_allocations.values())
        total_points = self.creation_points_combo.currentData() or 0
        all_points_allocated = total_points > 0 and spent == total_points
        self.next_button.setEnabled(all_points_allocated)
        self.character_setup_home.set_all_stat_points_allocated(
            all_points_allocated
        )
        self.creation_points_remaining_label.setText(
            f"Points remaining: {total_points - spent}"
        )

        for code, value_label in self.characteristic_value_labels.items():
            value_label.setText(str(self.generated_character.characteristics[code]))
            minus_button, plus_button = self.characteristic_buttons[code]
            minus_button.setEnabled(self._creation_allocations[code] > 0)
            plus_button.setEnabled(
                spent < total_points
                and self._creation_allocations[code] < self._max_creation_points
            )

    def _load_creation_point_options(self):
        document = self.game_data.get("creation_points", "creation_points") or {}
        points = document.get("creation_points", {})
        self.creation_points_combo.clear()
        self.creation_points_combo.addItem(
            f"Base ({points.get('base_points', 85)} points)",
            points.get("base_points", 85),
        )
        self.creation_points_combo.addItem(
            f"High Power ({points.get('high_power_option', 100)} points)",
            points.get("high_power_option", 100),
        )
        self._max_creation_points = points.get("max_per_characteristic", 20)

    def _build_characteristic_controls(self):
        while self.characteristic_grid.count():
            item = self.characteristic_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.characteristic_value_labels.clear()
        self.characteristic_buttons.clear()
        characteristic_document = (
            self.game_data.get("characteristics", "characteristics") or {}
        )
        characteristic_descriptions = {
            item.get("id", "").upper(): item.get("description", "")
            for item in characteristic_document.get("characteristics", [])
        }
        headers = ("Characteristic", "Total", "-", "+")
        for column, text in enumerate(headers):
            header = QLabel(text)
            header.setAlignment(Qt.AlignmentFlag.AlignCenter)
            header.setStyleSheet("font-weight: bold; padding: 4px;")
            if column < 2:
                font = header.font()
                font.setPointSizeF(font.pointSizeF() * 2)
                header.setFont(font)
            self.characteristic_grid.addWidget(header, 0, column)

        for row, code in enumerate(CHAR_CODES, start=1):
            name_label = QLabel(code)
            name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            name_label.setToolTip(characteristic_descriptions.get(code, ""))
            name_label.setStyleSheet(
                "QLabel:hover { color: #39ff14; }"
            )
            font = name_label.font()
            font.setPointSizeF(font.pointSizeF() * 2)
            name_label.setFont(font)
            self.characteristic_grid.addWidget(name_label, row, 0)

            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = value_label.font()
            font.setPointSizeF(font.pointSizeF() * 2)
            value_label.setFont(font)
            self.characteristic_grid.addWidget(value_label, row, 1)

            minus_button = QPushButton("-")
            plus_button = QPushButton("+")
            for button in (minus_button, plus_button):
                button.setFixedSize(44, 36)
            minus_button.clicked.connect(
                self._make_creation_point_adjuster(code, -1)
            )
            plus_button.clicked.connect(
                self._make_creation_point_adjuster(code, 1)
            )
            self.characteristic_grid.addWidget(minus_button, row, 2)
            self.characteristic_grid.addWidget(plus_button, row, 3)
            self.characteristic_value_labels[code] = value_label
            self.characteristic_buttons[code] = (minus_button, plus_button)

    def _make_creation_point_adjuster(self, code, amount):
        def adjust():
            self.adjust_creation_points(code, amount)

        return adjust

    def update_experience_tier(self):
        if not hasattr(self, "game_data"):
            return

        tiers_document = self.game_data.get("experience_tiers", "experience_tiers") or {}
        tiers = tiers_document.get("experience_tiers", {}).get("tiers", [])
        experience = self.experience_input.value()
        tier_number = 0
        luck_available = 0

        for tier in tiers:
            xp_range = tier.get("xp", "")
            if "+" in xp_range:
                lower_bound = int(xp_range.replace("+", "").replace(",", ""))
                if experience >= lower_bound:
                    tier_number = tier["tier"]
                    luck_available = tier.get("luck", 0)
            else:
                bounds = xp_range.replace("–", "-").replace(",", "").split("-")
                if len(bounds) == 2 and int(bounds[0]) <= experience <= int(bounds[1]):
                    tier_number = tier["tier"]
                    luck_available = tier.get("luck", 0)

        self._starting_luck = luck_available
        self.experience_tier_label.setText(f"Tier: {tier_number}")
        self.update_outlier_selection()
        self.refresh_selection_options()

    # ---------------------------------------------------------
    # Load soldier types based on mode
    # ---------------------------------------------------------
    def update_soldier_types(self):
        use_lns = self.selected_mode == "Light & Sky"
        self._selected_soldier_skills.clear()
        self.character_setup_home.equipment_or_light_powers_button.setText(
            "Light Abilities / Light Aspects" if use_lns else "Equipment"
        )
        loader = DataLoader(use_light_and_sky=use_lns)
        self.game_data = loader.load_all()
        self._load_creation_point_options()
        self.update_experience_tier()

        soldier_types = self.game_data.families.get("soldier_type", {})

        core_list = []
        human_list = []
        guardian_list = []

        for name, record in soldier_types.items():
            path = record.get("source_path", "")

            if "core/unsc_soldier_types" in path:
                core_list.append(name)

            if "light_and_sky/character_creation/human_soldier_types" in path:
                human_list.append(name)

            if "light_and_sky/character_creation/guardian_classes_subclasses" in path:
                guardian_list.append(name)

        self._core_names = core_list
        self._human_names = human_list
        self._guardian_names = guardian_list
        self.subclass_combo.clear()
        self.connection_combo.clear()

        if use_lns:
            self.connection_combo.addItem("")
            connections = self.game_data.get("connections", "connections") or {}
            connections = connections.get("connections", connections)
            for category in ("light", "darkness", "specialized"):
                self.connection_combo.addItems(
                    [item["name"] for item in connections.get(category, [])]
                )
        self.refresh_selection_options()
        self.update_subclasses()
        self._refresh_initial_setup_options()
        self._build_outlier_tiles()
        if use_lns:
            self._build_light_power_tiles()
        else:
            self._build_equipment_tiles()
        self.update_specialization_selection()

    @staticmethod
    def _add_costed_items(combo, names, records, available_xp):
        combo.addItem("")
        for name in names:
            cost = records[name].get("experience_cost", 0)
            if cost <= available_xp:
                combo.addItem(f"{records[name].get('name', name)} ({cost:,} XP)", name)

    def refresh_selection_options(self):
        if (
            not hasattr(self, "game_data")
            or not hasattr(self, "_core_names")
            or getattr(self, "_refreshing_options", False)
        ):
            return

        self._refreshing_options = True
        try:
            records = self.game_data.families.get("soldier_type", {})
            available_xp = self.experience_input.value()
            use_lns = self.selected_mode == "Light & Sky"
            selected_human = self.human_combo.currentData()
            selected_guardian = self.guardian_combo.currentData()

            self.soldier_combo.clear()
            self.human_combo.clear()
            self.guardian_combo.clear()

            if use_lns:
                self._add_costed_items(
                    self.human_combo, self._human_names, records, available_xp
                )
                human_cost = records.get(selected_human, {}).get("experience_cost", 0)
                guardian_xp = max(0, available_xp - human_cost)
                self._add_costed_items(
                    self.guardian_combo, self._guardian_names, records, guardian_xp
                )
                self._restore_combo_selection(self.human_combo, selected_human)
                self._restore_combo_selection(self.guardian_combo, selected_guardian)
            else:
                self._add_costed_items(
                    self.soldier_combo, self._core_names, records, available_xp
                )
                self.refresh_core_background_options()
            if use_lns:
                self.update_subclasses()
        finally:
            self._refreshing_options = False
        self._refresh_initial_setup_options()

    def refresh_core_background_options(self):
        if (
            not hasattr(self, "game_data")
            or getattr(self, "_refreshing_background_options", False)
            or self.selected_mode != "Core"
        ):
            return

        self._refreshing_background_options = True
        try:
            selected_upbringing = self.upbringing_combo.currentData()
            selected_environment = self.environment_combo.currentData()
            selected_lifestyles = [combo.currentData() for combo in self.lifestyle_combos]

            upbringing_records = (
                self.game_data.get("upbringing", "upbringing") or {}
            ).get("upbringing", [])
            environment_records = (
                self.game_data.get("environment", "environment") or {}
            ).get("environment", [])
            lifestyle_records = (
                self.game_data.get("lifestyle", "lifestyle") or {}
            ).get("lifestyle", [])

            self.upbringing_combo.blockSignals(True)
            self.environment_combo.blockSignals(True)
            for combo in self.lifestyle_combos:
                combo.blockSignals(True)
            self.upbringing_combo.clear()
            self.environment_combo.clear()
            for combo in self.lifestyle_combos:
                combo.clear()

            self.upbringing_combo.addItem("", "")
            for record in upbringing_records:
                self.upbringing_combo.addItem(record["name"], record["name"])
            self._restore_combo_selection(self.upbringing_combo, selected_upbringing)

            selected_record = next(
                (
                    record
                    for record in upbringing_records
                    if record["name"] == self.upbringing_combo.currentText()
                ),
                None,
            )
            available_environments = (
                selected_record.get("environment_available", ["Any"])
                if selected_record
                else ["Any"]
            )
            self.environment_combo.addItem("", "")
            for record in environment_records:
                if (
                    "Any" in available_environments
                    or record["name"] in available_environments
                ):
                    self.environment_combo.addItem(
                        record["name"], record["name"]
                    )
            self._restore_combo_selection(self.environment_combo, selected_environment)

            for combo, selected_lifestyle in zip(
                self.lifestyle_combos, selected_lifestyles
            ):
                combo.addItem("", "")
                for record in lifestyle_records:
                    combo.addItem(record["name"], record["name"])
                self._restore_combo_selection(combo, selected_lifestyle)
        finally:
            self.upbringing_combo.blockSignals(False)
            self.environment_combo.blockSignals(False)
            for combo in self.lifestyle_combos:
                combo.blockSignals(False)
            self._refreshing_background_options = False
        self._refresh_initial_setup_options()

    @staticmethod
    def _restore_combo_selection(combo, key):
        if key is None:
            return
        index = combo.findData(key)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ---------------------------------------------------------
    # Populate subclasses when a Guardian class is selected
    # ---------------------------------------------------------
    def update_subclasses(self):
        self.subclass_combo.clear()

        soldier_type = self.guardian_combo.currentData()
        if not soldier_type:
            self._refresh_initial_setup_options()
            return

        record = self.game_data.get("soldier_type", soldier_type)
        if not record:
            self._refresh_initial_setup_options()
            return

        path = record.get("source_path", "")

        # Only Guardian classes have subclasses
        if "guardian_classes_subclasses" in path:
            subclasses = record.get("subclasses", {})
            self.subclass_combo.addItems(list(subclasses.keys()))
        else:
            # No subclasses for UNSC or Human soldier types
            self.subclass_combo.clear()
        self._refresh_initial_setup_options()

    # ---------------------------------------------------------
    # Generate character
    # ---------------------------------------------------------
    def generate_character(self):
        self.character_setup_home.set_character_ready_to_export(False)
        name = "Test Character"
        use_lns = self.selected_mode == "Light & Sky"
        if use_lns:
            human_type = self.human_combo.currentData()
            guardian_type = self.guardian_combo.currentData()
            soldier_type = guardian_type or human_type
            subclass = self.subclass_combo.currentText() or None
            if not guardian_type:
                subclass = None
            connection = self.connection_combo.currentText() or None
        else:
            soldier_type = self.soldier_combo.currentData()
            self._selected_core_soldier = soldier_type
            subclass = None
            connection = None

        generator = CharacterGenerator(self.game_data, use_light_and_sky=use_lns)
        selected_soldier_types = (
            [human_type, guardian_type]
            if use_lns
            else [soldier_type]
        )
        skill_training = {}
        for selected_type in selected_soldier_types:
            for skill, bonus in self._selected_soldier_skills.get(
                selected_type, {}
            ).items():
                skill_training[skill] = max(
                    skill_training.get(skill, 0), bonus
                )

        char = generator.generate(
            name=name,
            soldier_type=soldier_type,
            subclass=subclass,
            human_soldier_type=human_type if use_lns else None,
            guardian_class=guardian_type if use_lns else None,
            connection=connection,
            upbringing=(self.upbringing_combo.currentData() if not use_lns else None),
            environment=(self.environment_combo.currentData() if not use_lns else None),
            lifestyles=(
                [combo.currentData() for combo in self.lifestyle_combos if combo.currentData()]
                if not use_lns
                else None
            ),
            starting_experience=self.experience_input.value(),
            skill_training=skill_training or None,
        )

        self.generated_character = char
        self._pre_outlier_characteristics = char.characteristics.copy()
        self._pre_outlier_mythic_characteristics = (
            char.mythic_characteristics.copy()
        )
        self._outlier_characteristics.clear()

        # Reset per-character creation state so a regenerated character
        # never inherits selections from the previous one.
        for attr in ("_pre_specialization_skills", "_pre_specialization_abilities"):
            if hasattr(self, attr):
                delattr(self, attr)
        self._light_xp_spent = 0
        self._selected_light_category = None
        self._selected_light_aspects = {}
        self._selected_light_powers = {}
        self._selected_light_supers = {}
        for tile, _, _ in self.outlier_tiles:
            tile.blockSignals(True)
            tile.setChecked(False)
            tile.blockSignals(False)
        for button, _ in self.specialization_tiles:
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)

        if use_lns:
            self._build_light_power_tiles()
        else:
            self._build_equipment_tiles()
        self._generated_characteristics = char.characteristics.copy()
        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self._build_characteristic_controls()

        self._update_creation_point_display()
        self.pages.setCurrentWidget(self.creation_page)


# ---------------------------------------------------------
# Run UI
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestGeneratorUI()
    window.showMaximized()
    sys.exit(app.exec())
