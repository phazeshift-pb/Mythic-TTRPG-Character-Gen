from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QFrame,
    QStackedWidget, QGridLayout, QGroupBox,
)
import sys

from PySide6.QtCore import Qt
from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.character import CHAR_CODES
from src.ui.character_setup_home import CharacterSetupHome
from src.ui.equipment_page import EquipmentPage
from src.ui.landing_page import LandingPage
from src.ui.initial_character_setup import InitialCharacterSetupPage
from src.ui.outlier_page import OutlierPage
from src.ui.specialization_page import DelayedTooltipLabel, SpecializationPage
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
        self.page_widgets = (
            self.landing_page,
            self.character_setup_home,
            self.version_and_expansions_page,
            self.initial_character_setup_page,
            self.creation_page,
            self.specialization_page,
            self.outlier_page,
            self.equipment_page,
        )
        for page in self.page_widgets:
            self.pages.addWidget(page)
        layout.addWidget(self.pages)

        self.create_character_button = self.landing_page.create_character_button
        self.load_character_button = self.landing_page.load_character_button

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
            self.update_soldier_types
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
        self.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.initial_character_setup_page)
        )
        self.creation_points_combo.currentIndexChanged.connect(
            self.reset_creation_points
        )
        self.reset_creation_button.clicked.connect(self.reset_creation_points)
        self.next_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.specialization_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.specialization_done_button.clicked.connect(
            self.finish_specialization_selection
        )
        self.outlier_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
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

        self._creation_allocations = {code: 0 for code in CHAR_CODES}

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
                tile = QGroupBox(outlier["name"])
                tile.setCheckable(True)
                tile.setChecked(False)
                tile.setMinimumHeight(105)
                tile.setMaximumHeight(105)
                tile.setStyleSheet(
                    "QGroupBox { background-color: #dfe8cd; "
                    "border: 1px solid #f4f2e8; color: #ffffff; "
                    "font-weight: bold; padding-top: 22px; }"
                    "QGroupBox::title { subcontrol-origin: margin; "
                    "subcontrol-position: top center; background-color: #526b28; "
                    "color: #ffffff; padding: 4px 8px; }"
                    "QGroupBox:checked { background-color: #c7dc9c; "
                    "border: 3px solid #f7d36b; }"
                )
                tile_layout = QVBoxLayout(tile)
                effect_label = QLabel(outlier["effect"])
                effect_label.setWordWrap(True)
                effect_label.setStyleSheet("color: #ffffff; padding: 4px;")
                tile_layout.addWidget(effect_label)
                tile.toggled.connect(self.update_outlier_selection)
                self.outlier_tiles.append((tile, outlier, luck_cost))
                self.outlier_grid.addWidget(tile, row + index // 3, index % 3)

            row += (len(outliers) + 2) // 3 + 1

    def update_outlier_selection(self):
        selected_count = sum(tile.isChecked() for tile, _, _ in self.outlier_tiles)
        luck_cost = sum(cost for tile, _, cost in self.outlier_tiles if tile.isChecked())
        self.outlier_done_button.setText(f"Done ({selected_count}; Burn {luck_cost} Luck)")

    def finish_outlier_selection(self):
        if hasattr(self, "generated_character"):
            self.generated_character.outliers = []
            self.generated_character.luck_burned = 0
            for tile, outlier, luck_cost in self.outlier_tiles:
                if tile.isChecked():
                    self.generated_character.apply_outlier(outlier, luck_cost)
        if self.selected_mode == "Core" and self.equipment_tiles:
            self.update_equipment_selection()
            self.pages.setCurrentWidget(self.equipment_page)
        elif self.selected_mode == "Light & Sky":
            self._build_light_power_tiles()
            self.update_light_power_selection()
            self.pages.setCurrentWidget(self.equipment_page)
        else:
            self.pages.setCurrentWidget(self.creation_page)

    def _build_equipment_tiles(self):
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
        if self.selected_mode == "Light & Sky":
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
        self.pages.setCurrentWidget(self.creation_page)

    def _clear_equipment_grid(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _build_light_power_tiles(self):
        self._clear_equipment_grid()
        self.equipment_tiles.clear()
        self.light_aspect_tiles.clear()
        self.light_ability_tiles.clear()
        self.equipment_page_title.setText("LIGHT ASPECTS AND ABILITIES")
        self.equipment_done_button.setText("Done")

        aspects_document = self.game_data.get("light_aspects", "light_aspects") or {}
        aspects_by_connection = aspects_document.get("light_aspects", {})
        selected_connection = self.connection_combo.currentText()
        selected_class = self.guardian_combo.currentText()
        ability_document = self.game_data.get(
            "light_abilities", "light_abilities_and_grenades"
        ) or {}
        abilities = ability_document.get("abilities", [])

        row = 0
        aspect_header = QLabel("ASPECTS (1 STARTING SLOT)")
        aspect_header.setStyleSheet(
            "color: #f2f0e6; font-weight: bold; font-size: 14px;"
        )
        self.equipment_grid.addWidget(aspect_header, row, 0, 1, 3)
        row += 1

        all_aspects = [
            (connection.title(), aspect)
            for connection, records in aspects_by_connection.items()
            if isinstance(records, list)
            for aspect in records
        ]
        for index, (connection, aspect) in enumerate(all_aspects):
            tile, select_button = self._create_selection_tile(
                aspect["name"],
                f"{connection} | XP {self._light_aspect_cost(aspect, connection)}\n"
                f"{aspect['description']}",
                min_height=145,
            )
            select_button.toggled.connect(
                lambda checked, selected_tile=select_button: self._select_light_tile(
                    selected_tile, "aspect", checked
                )
            )
            self.light_aspect_tiles.append((select_button, aspect, connection))
            self.equipment_grid.addWidget(tile, row + index // 3, index % 3)

        row += (len(all_aspects) + 2) // 3 + 1
        ability_header = QLabel("LIGHT ABILITIES (2 STARTING SLOTS)")
        ability_header.setStyleSheet(
            "color: #f2f0e6; font-weight: bold; font-size: 14px;"
        )
        self.equipment_grid.addWidget(ability_header, row, 0, 1, 3)
        row += 1

        available_abilities = [
            ability for ability in abilities
            if ability.get("connection") in ("Universal", selected_connection)
            and ability.get("class") in ("All", selected_class)
        ]
        for index, ability in enumerate(available_abilities):
            tile, select_button = self._create_selection_tile(
                ability["name"],
                f"{ability.get('category', 'Ability')} | "
                f"XP {ability.get('experience_cost', 0)} | "
                f"Light {ability.get('light_cost', 'N/A')}\n"
                f"{ability['description']}",
                min_height=145,
            )
            select_button.toggled.connect(
                lambda checked, selected_tile=select_button: self._select_light_tile(
                    selected_tile, "ability", checked
                )
            )
            self.light_ability_tiles.append((select_button, ability))
            self.equipment_grid.addWidget(tile, row + index // 3, index % 3)

    def _create_selection_tile(self, title, text, min_height=125):
        card = QFrame(self.equipment_content)
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
        select_button.setMinimumHeight(56)
        select_button.setStyleSheet(
            "QPushButton { text-align: left; background-color: #526b28; "
            "color: #ffffff; border: 2px solid #788f3e; border-radius: 6px; "
            "padding: 10px 14px; font-size: 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #788f3e; "
            "border-color: #f7d36b; }"
            "QPushButton:checked { background-color: #35451d; "
            "border: 3px solid #f7d36b; }"
            "QPushButton:pressed { background-color: #35451d; "
            "border-color: #f7d36b; }"
        )
        layout.addWidget(select_button)

        description = QLabel(text, card)
        description.setWordWrap(True)
        description.setStyleSheet(
            "color: #d5d2c6; border: none; padding: 4px 8px 8px 8px;"
        )
        layout.addWidget(description)

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

    def _light_aspect_cost(self, aspect, connection):
        selected_connection = self.connection_combo.currentText()
        cost = aspect.get("experience_cost", 0)
        return cost if connection == selected_connection else cost * 2

    def _select_light_tile(self, selected_tile, power_type, checked):
        if checked:
            tiles = (
                self.light_aspect_tiles
                if power_type == "aspect"
                else self.light_ability_tiles
            )
            selected_count = sum(button.isChecked() for button, *_ in tiles)
            limit = 1 if power_type == "aspect" else 2
            if selected_count > limit:
                selected_tile.blockSignals(True)
                selected_tile.setChecked(False)
                selected_tile.blockSignals(False)
        self.update_light_power_selection()

    def update_light_power_selection(self):
        aspect_count = sum(button.isChecked() for button, *_ in self.light_aspect_tiles)
        ability_count = sum(button.isChecked() for button, *_ in self.light_ability_tiles)
        self.equipment_done_button.setText(
            f"Done (Aspects {aspect_count}/1; Abilities {ability_count}/2)"
        )

    def finish_light_power_selection(self):
        if hasattr(self, "generated_character"):
            aspects = [
                aspect
                for button, aspect, _ in self.light_aspect_tiles
                if button.isChecked()
            ]
            abilities = [
                ability
                for button, ability in self.light_ability_tiles
                if button.isChecked()
            ]
            self.generated_character.apply_light_powers(aspects, abilities)
        self.pages.setCurrentWidget(self.creation_page)

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

        for tier in tiers:
            xp_range = tier.get("xp", "")
            if "+" in xp_range:
                lower_bound = int(xp_range.replace("+", "").replace(",", ""))
                if experience >= lower_bound:
                    tier_number = tier["tier"]
            else:
                bounds = xp_range.replace("–", "-").replace(",", "").split("-")
                if len(bounds) == 2 and int(bounds[0]) <= experience <= int(bounds[1]):
                    tier_number = tier["tier"]

        self.experience_tier_label.setText(f"Tier: {tier_number}")
        self.refresh_selection_options()

    # ---------------------------------------------------------
    # Load soldier types based on mode
    # ---------------------------------------------------------
    def update_soldier_types(self):
        use_lns = self.selected_mode == "Light & Sky"
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
        )

        self.generated_character = char
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
