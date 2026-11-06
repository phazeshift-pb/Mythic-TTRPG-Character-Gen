# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Specialization pack selection.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from src.ui.specialization_page import DelayedTooltipLabel
from src.ui import theme


class SpecializationMixin:
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
                theme.TILE_TITLE
            )
            self.specialization_grid.addWidget(section_label, row, 0, 1, 3)
            row += 1

            for index, pack in enumerate(packs):
                column = index % 3
                tile_row = row + index // 3
                tile = QFrame(self.specialization_content)
                tile.setStyleSheet(
                    theme.TILE_FRAME
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

    def _soldier_takes_no_specialization(self):
        """Smart AI: no Specialization Pack (its four +10 Skills stand in for one)."""
        character = getattr(self, "generated_character", None)
        if character is None or not hasattr(self, "game_data"):
            return False
        for record in self.game_data.families.get("soldier_type", {}).values():
            if isinstance(record, dict) and record.get("name") == character.soldier_type:
                return bool((record.get("special_rules") or {}).get("no_specialization_pack"))
        return False

    def update_specialization_selection(self):
        if self.selected_mode == "Light & Sky":
            button_text = "Next: Light Abilities / Light Aspects"
        else:
            button_text = "Next: Equipment Packs"
        no_pack = self._soldier_takes_no_specialization()
        if no_pack:
            button_text += " (this Soldier Type takes no Specialization Pack)"
        for button, _ in self.specialization_tiles:
            if no_pack and button.isChecked():
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
            button.setEnabled(not no_pack)
        self.specialization_done_button.setText(button_text)
        has_selection = no_pack or any(
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
