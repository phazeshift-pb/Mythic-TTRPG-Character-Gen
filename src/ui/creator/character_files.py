# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Loading, saving and exporting character files.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

import json
import os
import re
import tempfile
from dataclasses import asdict
from pathlib import Path

from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from src.data_loader import DataLoader


class CharacterFilesMixin:
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

        character = export_data["character"]
        if character.get("creation_experience") is None:
            # Files saved before the XP Shop: creation XP is in the selections.
            selections = export_data.get("selections") or {}
            starting_xp = selections.get("starting_xp")
            if isinstance(starting_xp, int):
                character["creation_experience"] = starting_xp
        self.character_sheet.set_character(character, ruleset, character_game_data)
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
                "background_choices": {
                    category: self._background_choices_for(
                        category, selected_value(combo)
                    )
                    for category, combo in (
                        ("upbringing", self.upbringing_combo),
                        ("environment", self.environment_combo),
                    )
                    if selected_value(combo)
                    and self._background_choices_for(category, selected_value(combo))
                },
                "lifestyles": [
                    selected_value(combo)
                    for combo in self.lifestyle_combos
                    if selected_value(combo)
                ],
                "skill_training": self._selected_soldier_skills.get(
                    selected_value(self.soldier_combo), {}
                ),
            }
            pack = next(
                (
                    name
                    for button, name, _ in self.equipment_tiles
                    if button.isChecked()
                ),
                None,
            )
            stored = getattr(self, "_equipment_pack_choices", {}) or {}
            equipment = {
                "pack": pack,
                "choices": list(stored.get("choices", []))
                if pack and stored.get("name") == pack
                else [],
            }
            if stored.get("starting_armor"):
                equipment["starting_armor"] = dict(stored["starting_armor"])

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
                "outliers": self._selected_outlier_names(),
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
        self.reset_character_creator()
        self.pages.setCurrentWidget(self.landing_page)
