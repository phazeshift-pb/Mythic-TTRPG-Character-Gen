from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QSpinBox,
    QStackedWidget, QGridLayout, QGroupBox, QScrollArea
)
import sys

from PySide6.QtCore import Qt
from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.character import CHAR_CODES


class TestGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mythic Character Generator Test UI")
        self.resize(700, 550)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        self.selection_page = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_page)
        self.pages.addWidget(self.selection_page)

        # ---------------------------------------------------------
        # Starting experience and automatic tier
        # ---------------------------------------------------------
        experience_row = QHBoxLayout()
        experience_label = QLabel("Starting XP:")
        self.experience_input = QSpinBox()
        self.experience_input.setRange(0, 10_000_000)
        self.experience_input.setValue(0)
        self.experience_input.valueChanged.connect(self.update_experience_tier)
        self.experience_tier_label = QLabel("Tier: 0")
        experience_row.addWidget(experience_label)
        experience_row.addWidget(self.experience_input)
        experience_row.addWidget(self.experience_tier_label)
        self.selection_layout.addLayout(experience_row)

        # ---------------------------------------------------------
        # Mode selection (Core vs Light & Sky)
        # ---------------------------------------------------------
        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Core", "Light & Sky"])
        self.mode_combo.currentIndexChanged.connect(self.update_soldier_types)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo)
        self.selection_layout.addLayout(mode_row)

        # ---------------------------------------------------------
        # Core soldier type selection
        # ---------------------------------------------------------
        st_row = QHBoxLayout()
        st_label = QLabel("Soldier Type:")
        self.soldier_combo = QComboBox()

        st_row.addWidget(st_label)
        st_row.addWidget(self.soldier_combo)
        self.selection_layout.addLayout(st_row)
        self.core_soldier_row = st_row
        self.soldier_label = st_label

        # ---------------------------------------------------------
        # Core background selections
        # ---------------------------------------------------------
        upbringing_row = QHBoxLayout()
        self.upbringing_label = QLabel("Upbringing:")
        self.upbringing_combo = QComboBox()
        self.upbringing_combo.currentIndexChanged.connect(
            self.refresh_core_background_options
        )
        upbringing_row.addWidget(self.upbringing_label)
        upbringing_row.addWidget(self.upbringing_combo)
        self.selection_layout.addLayout(upbringing_row)

        environment_row = QHBoxLayout()
        self.environment_label = QLabel("Environment:")
        self.environment_combo = QComboBox()
        environment_row.addWidget(self.environment_label)
        environment_row.addWidget(self.environment_combo)
        self.selection_layout.addLayout(environment_row)

        lifestyle_row = QHBoxLayout()
        self.lifestyle_label = QLabel("Lifestyle 1:")
        self.lifestyle_combo = QComboBox()
        lifestyle_row.addWidget(self.lifestyle_label)
        lifestyle_row.addWidget(self.lifestyle_combo)
        self.selection_layout.addLayout(lifestyle_row)

        lifestyle_two_row = QHBoxLayout()
        self.lifestyle_two_label = QLabel("Lifestyle 2:")
        self.lifestyle_two_combo = QComboBox()
        lifestyle_two_row.addWidget(self.lifestyle_two_label)
        lifestyle_two_row.addWidget(self.lifestyle_two_combo)
        self.selection_layout.addLayout(lifestyle_two_row)

        lifestyle_three_row = QHBoxLayout()
        self.lifestyle_three_label = QLabel("Lifestyle 3:")
        self.lifestyle_three_combo = QComboBox()
        lifestyle_three_row.addWidget(self.lifestyle_three_label)
        lifestyle_three_row.addWidget(self.lifestyle_three_combo)
        self.selection_layout.addLayout(lifestyle_three_row)

        self.lifestyle_combos = (
            self.lifestyle_combo,
            self.lifestyle_two_combo,
            self.lifestyle_three_combo,
        )

        self.core_background_widgets = (
            self.upbringing_label,
            self.upbringing_combo,
            self.environment_label,
            self.environment_combo,
            self.lifestyle_label,
            self.lifestyle_two_label,
            self.lifestyle_three_label,
            *self.lifestyle_combos,
        )

        # ---------------------------------------------------------
        # Light & Sky soldier type selections
        # ---------------------------------------------------------
        human_row = QHBoxLayout()
        self.human_label = QLabel("Human Soldier Type:")
        self.human_combo = QComboBox()
        self.human_combo.currentIndexChanged.connect(self.refresh_selection_options)
        human_row.addWidget(self.human_label)
        human_row.addWidget(self.human_combo)
        self.selection_layout.addLayout(human_row)

        guardian_row = QHBoxLayout()
        self.guardian_label = QLabel("Guardian Class Soldier Type:")
        self.guardian_combo = QComboBox()
        self.guardian_combo.currentIndexChanged.connect(self.update_subclasses)
        guardian_row.addWidget(self.guardian_label)
        guardian_row.addWidget(self.guardian_combo)
        self.selection_layout.addLayout(guardian_row)

        # ---------------------------------------------------------
        # Subclass selection (only for Guardian classes)
        # ---------------------------------------------------------
        sub_row = QHBoxLayout()
        sub_label = QLabel("Subclass:")
        self.subclass_combo = QComboBox()

        sub_row.addWidget(sub_label)
        sub_row.addWidget(self.subclass_combo)
        self.selection_layout.addLayout(sub_row)
        self.subclass_label = sub_label

        connection_row = QHBoxLayout()
        self.connection_label = QLabel("Connection:")
        self.connection_combo = QComboBox()
        connection_row.addWidget(self.connection_label)
        connection_row.addWidget(self.connection_combo)
        self.selection_layout.addLayout(connection_row)

        self.human_row_widgets = (self.human_label, self.human_combo)
        self.guardian_row_widgets = (self.guardian_label, self.guardian_combo)

        # ---------------------------------------------------------
        # Generate button
        # ---------------------------------------------------------
        self.generate_button = QPushButton("Generate Character")
        self.generate_button.clicked.connect(self.generate_character)
        self.selection_layout.addWidget(self.generate_button)

        # ---------------------------------------------------------
        # Creation point allocation page
        # ---------------------------------------------------------
        self.creation_page = QWidget()
        creation_layout = QVBoxLayout(self.creation_page)
        self.pages.addWidget(self.creation_page)

        creation_header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.selection_page))
        self.creation_points_combo = QComboBox()
        self.creation_points_combo.currentIndexChanged.connect(self.reset_creation_points)
        self.reset_creation_button = QPushButton("Reset Points")
        self.reset_creation_button.clicked.connect(self.reset_creation_points)
        self.creation_points_remaining_label = QLabel("Points remaining: 0")
        self.specialization_button = QPushButton("Specialization Packs")
        self.specialization_button.clicked.connect(self.open_specialization_page)
        self.equipment_button = QPushButton("Equipment Pack")
        self.equipment_button.clicked.connect(self.open_equipment_page)
        creation_header.addWidget(self.back_button)
        creation_header.addWidget(QLabel("Creation points:"))
        creation_header.addWidget(self.creation_points_combo)
        creation_header.addWidget(self.reset_creation_button)
        creation_header.addWidget(self.creation_points_remaining_label)
        creation_header.addWidget(self.specialization_button)
        creation_header.addWidget(self.equipment_button)
        creation_layout.addLayout(creation_header)

        self.characteristic_grid = QGridLayout()
        self.characteristic_value_labels = {}
        self.characteristic_buttons = {}
        creation_layout.addLayout(self.characteristic_grid)

        # Output log
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        creation_layout.addWidget(self.output)

        # ---------------------------------------------------------
        # Specialization pack selection page
        # ---------------------------------------------------------
        self.specialization_page = QWidget()
        specialization_layout = QVBoxLayout(self.specialization_page)
        self.pages.addWidget(self.specialization_page)

        specialization_header = QHBoxLayout()
        specialization_header.addWidget(QLabel("SPECIALIZATION PACKS"))
        specialization_header.addStretch()
        self.specialization_back_button = QPushButton("Back")
        self.specialization_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.specialization_done_button = QPushButton("Done")
        self.specialization_done_button.clicked.connect(
            self.finish_specialization_selection
        )
        specialization_header.addWidget(self.specialization_back_button)
        specialization_header.addWidget(self.specialization_done_button)
        specialization_layout.addLayout(specialization_header)

        self.specialization_scroll = QScrollArea()
        self.specialization_scroll.setWidgetResizable(True)
        self.specialization_content = QWidget()
        self.specialization_content.setStyleSheet("background-color: #242424;")
        self.specialization_grid = QGridLayout(self.specialization_content)
        self.specialization_grid.setSpacing(18)
        self.specialization_grid.setColumnStretch(0, 1)
        self.specialization_grid.setColumnStretch(1, 1)
        self.specialization_grid.setColumnStretch(2, 1)
        self.specialization_scroll.setWidget(self.specialization_content)
        specialization_layout.addWidget(self.specialization_scroll)
        self.specialization_tiles = []

        # ---------------------------------------------------------
        # Outlier selection page
        # ---------------------------------------------------------
        self.outlier_page = QWidget()
        outlier_layout = QVBoxLayout(self.outlier_page)
        self.pages.addWidget(self.outlier_page)

        outlier_header = QHBoxLayout()
        outlier_header.addWidget(QLabel("OUTLIERS"))
        outlier_header.addStretch()
        self.outlier_back_button = QPushButton("Back")
        self.outlier_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.outlier_done_button = QPushButton("Done")
        self.outlier_done_button.clicked.connect(self.finish_outlier_selection)
        outlier_header.addWidget(self.outlier_back_button)
        outlier_header.addWidget(self.outlier_done_button)
        outlier_layout.addLayout(outlier_header)

        self.outlier_scroll = QScrollArea()
        self.outlier_scroll.setWidgetResizable(True)
        self.outlier_content = QWidget()
        self.outlier_content.setStyleSheet("background-color: #242424;")
        self.outlier_grid = QGridLayout(self.outlier_content)
        self.outlier_grid.setSpacing(18)
        for column in range(3):
            self.outlier_grid.setColumnStretch(column, 1)
        self.outlier_scroll.setWidget(self.outlier_content)
        outlier_layout.addWidget(self.outlier_scroll)
        self.outlier_tiles = []

        # ---------------------------------------------------------
        # Core equipment pack selection page
        # ---------------------------------------------------------
        self.equipment_page = QWidget()
        equipment_layout = QVBoxLayout(self.equipment_page)
        self.pages.addWidget(self.equipment_page)

        equipment_header = QHBoxLayout()
        self.equipment_page_title = QLabel("EQUIPMENT PACK")
        equipment_header.addWidget(self.equipment_page_title)
        equipment_header.addStretch()
        self.equipment_back_button = QPushButton("Back")
        self.equipment_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.equipment_done_button = QPushButton("Done")
        self.equipment_done_button.clicked.connect(self.finish_equipment_selection)
        equipment_header.addWidget(self.equipment_back_button)
        equipment_header.addWidget(self.equipment_done_button)
        equipment_layout.addLayout(equipment_header)

        self.equipment_scroll = QScrollArea()
        self.equipment_scroll.setWidgetResizable(True)
        self.equipment_content = QWidget()
        self.equipment_content.setStyleSheet("background-color: #242424;")
        self.equipment_grid = QGridLayout(self.equipment_content)
        self.equipment_grid.setSpacing(18)
        for column in range(3):
            self.equipment_grid.setColumnStretch(column, 1)
        self.equipment_scroll.setWidget(self.equipment_content)
        equipment_layout.addWidget(self.equipment_scroll)
        self.equipment_tiles = []
        self.light_aspect_tiles = []
        self.light_ability_tiles = []

        # Load initial data
        self.update_soldier_types()
        self._build_specialization_pack_tiles()
        self._build_outlier_tiles()
        self._build_equipment_tiles()

    def _build_specialization_pack_tiles(self):
        while self.specialization_grid.count():
            item = self.specialization_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.specialization_tiles.clear()
        document = self.game_data.get(
            "specialization_packs", "specialization_packs"
        ) if hasattr(self, "game_data") else None
        if not document:
            return

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
                tile = QGroupBox(pack["name"])
                tile.setCheckable(True)
                tile.setChecked(False)
                tile.setStyleSheet(
                    "QGroupBox {"
                    " background-color: #dfe8cd;"
                    " border: 1px solid #f4f2e8;"
                    " color: #ffffff;"
                    " font-weight: bold;"
                    " padding-top: 22px;"
                    "}"
                    "QGroupBox::title {"
                    " subcontrol-origin: margin;"
                    " subcontrol-position: top center;"
                    " background-color: #526b28;"
                    " color: #ffffff;"
                    " padding: 4px 8px;"
                    "}"
                    "QGroupBox:checked {"
                    " background-color: #c7dc9c;"
                    " border: 3px solid #f7d36b;"
                    "}"
                    "QGroupBox:checked::title { background-color: #788f3e; }"
                    "QGroupBox::indicator { width: 14px; height: 14px; }"
                )
                tile.setMinimumHeight(145)
                tile.setMaximumHeight(145)
                tile_layout = QGridLayout(tile)
                tile_layout.setContentsMargins(5, 5, 5, 5)
                tile_layout.setHorizontalSpacing(0)
                tile_layout.setVerticalSpacing(1)
                tile_layout.setColumnStretch(0, 1)
                tile_layout.setColumnStretch(1, 1)
                header_style = (
                    "color: #ffffff; background-color: #526b28; "
                    "font-weight: bold; padding: 3px;"
                )
                cell_style = "color: #ffffff; padding: 3px;"
                ability_header = QLabel("ABILITY")
                ability_header.setStyleSheet(header_style)
                skill_header = QLabel("SKILL")
                skill_header.setStyleSheet(header_style)
                tile_layout.addWidget(ability_header, 0, 0)
                tile_layout.addWidget(skill_header, 0, 1)

                for index, (ability, skill) in enumerate(
                    zip(pack.get("abilities", []), pack.get("skills", [])),
                    start=1,
                ):
                    ability_label = QLabel(ability)
                    ability_label.setStyleSheet(cell_style)
                    skill_label = QLabel(skill)
                    skill_label.setStyleSheet(cell_style)
                    tile_layout.addWidget(ability_label, index, 0)
                    tile_layout.addWidget(skill_label, index, 1)

                tile.toggled.connect(self.update_specialization_selection)
                self.specialization_tiles.append((tile, pack["name"]))
                self.specialization_grid.addWidget(tile, tile_row, column)

            row += (len(packs) + 2) // 3 + 1

    def update_specialization_selection(self):
        selected_count = sum(tile.isChecked() for tile, _ in self.specialization_tiles)
        self.specialization_done_button.setText(f"Done ({selected_count})")

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
                name for tile, name in self.specialization_tiles if tile.isChecked()
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
            self.output.append(
                "Specialization packs: "
                + (", ".join(self.generated_character.specialization_packs) or "None")
            )
            for ability in self.generated_character.abilities:
                self.output.append(f"Ability: {ability}")
            for skill_name, skill_value in self.generated_character.skills.items():
                self.output.append(f"Skill: {skill_name} (+{skill_value})")
        self.update_outlier_selection()
        self.pages.setCurrentWidget(self.outlier_page)

    def _build_outlier_tiles(self):
        while self.outlier_grid.count():
            item = self.outlier_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.outlier_tiles.clear()
        documents = [("CORE", "outliers", 1)]
        if self.mode_combo.currentText() == "Light & Sky":
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
            self.output.append(
                "Outliers: "
                + (", ".join(self.generated_character.outliers) or "None")
            )
            self.output.append(
                f"Luck burned on outliers: {self.generated_character.luck_burned}"
            )
        if self.mode_combo.currentText() == "Core" and self.equipment_tiles:
            self.update_equipment_selection()
            self.pages.setCurrentWidget(self.equipment_page)
        elif self.mode_combo.currentText() == "Light & Sky":
            self._build_light_power_tiles()
            self.update_light_power_selection()
            self.pages.setCurrentWidget(self.equipment_page)
        else:
            self.pages.setCurrentWidget(self.creation_page)

    def _build_equipment_tiles(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.equipment_tiles.clear()
        if self.mode_combo.currentText() != "Core" or not hasattr(self, "game_data"):
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
            tile = QGroupBox(pack_name.replace("_", " ").title())
            tile.setCheckable(True)
            tile.setChecked(False)
            tile.setMinimumHeight(145)
            tile.setMaximumHeight(145)
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
            item_label = QLabel("\n".join(items))
            item_label.setWordWrap(True)
            item_label.setStyleSheet("color: #ffffff; padding: 4px;")
            tile_layout.addWidget(item_label)
            tile.toggled.connect(
                lambda checked, selected_tile=tile: self.select_equipment_tile(
                    selected_tile, checked
                )
            )
            self.equipment_tiles.append((tile, pack_name, items))
            self.equipment_grid.addWidget(tile, index // 3, index % 3)

    def select_equipment_tile(self, selected_tile, checked):
        if checked:
            for tile, _, _ in self.equipment_tiles:
                if tile is not selected_tile:
                    tile.blockSignals(True)
                    tile.setChecked(False)
                    tile.blockSignals(False)
        self.update_equipment_selection()

    def update_equipment_selection(self):
        selected = next(
            (pack_name for tile, pack_name, _ in self.equipment_tiles if tile.isChecked()),
            None,
        )
        self.equipment_done_button.setText(
            f"Done ({selected.replace('_', ' ').title()})" if selected else "Done"
        )

    def open_equipment_page(self):
        if self.mode_combo.currentText() == "Light & Sky":
            self._build_light_power_tiles()
            self.update_light_power_selection()
        else:
            self._build_equipment_tiles()
            self.update_equipment_selection()
        self.pages.setCurrentWidget(self.equipment_page)

    def finish_equipment_selection(self):
        if self.mode_combo.currentText() == "Light & Sky":
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
                self.output.append(f"Equipment pack: {selected[0]}")
                for item in selected[1]:
                    self.output.append(f"Equipment: {item}")
            else:
                self.output.append("Equipment pack: None")
        self.pages.setCurrentWidget(self.creation_page)

    def _clear_equipment_grid(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

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
            tile = self._create_light_power_tile(
                aspect["name"],
                f"{connection} | XP {self._light_aspect_cost(aspect, connection)}\n"
                f"{aspect['description']}",
            )
            tile.toggled.connect(
                lambda checked, selected_tile=tile: self._select_light_tile(
                    selected_tile, "aspect", checked
                )
            )
            self.light_aspect_tiles.append((tile, aspect, connection))
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
            tile = self._create_light_power_tile(
                ability["name"],
                f"{ability.get('category', 'Ability')} | "
                f"XP {ability.get('experience_cost', 0)} | "
                f"Light {ability.get('light_cost', 'N/A')}\n"
                f"{ability['description']}",
            )
            tile.toggled.connect(
                lambda checked, selected_tile=tile: self._select_light_tile(
                    selected_tile, "ability", checked
                )
            )
            self.light_ability_tiles.append((tile, ability))
            self.equipment_grid.addWidget(tile, row + index // 3, index % 3)

    @staticmethod
    def _create_light_power_tile(title, text):
        tile = QGroupBox(title)
        tile.setCheckable(True)
        tile.setChecked(False)
        tile.setMinimumHeight(125)
        tile.setMaximumHeight(125)
        tile.setStyleSheet(
            "QGroupBox { background-color: #dfe8cd; border: 1px solid #f4f2e8; "
            "color: #ffffff; font-weight: bold; padding-top: 22px; }"
            "QGroupBox::title { subcontrol-origin: margin; "
            "subcontrol-position: top center; background-color: #526b28; "
            "color: #ffffff; padding: 4px 8px; }"
            "QGroupBox:checked { background-color: #c7dc9c; "
            "border: 3px solid #f7d36b; }"
        )
        layout = QVBoxLayout(tile)
        label = QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet("color: #ffffff; padding: 4px;")
        layout.addWidget(label)
        return tile

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
            selected_count = sum(tile.isChecked() for tile, *_ in tiles)
            limit = 1 if power_type == "aspect" else 2
            if selected_count > limit:
                selected_tile.blockSignals(True)
                selected_tile.setChecked(False)
                selected_tile.blockSignals(False)
        self.update_light_power_selection()

    def update_light_power_selection(self):
        aspect_count = sum(tile.isChecked() for tile, *_ in self.light_aspect_tiles)
        ability_count = sum(tile.isChecked() for tile, *_ in self.light_ability_tiles)
        self.equipment_done_button.setText(
            f"Done (Aspects {aspect_count}/1; Abilities {ability_count}/2)"
        )

    def finish_light_power_selection(self):
        if hasattr(self, "generated_character"):
            aspects = [
                aspect for tile, aspect, _ in self.light_aspect_tiles if tile.isChecked()
            ]
            abilities = [
                ability for tile, ability in self.light_ability_tiles if tile.isChecked()
            ]
            self.generated_character.apply_light_powers(aspects, abilities)
            self.output.append(
                "Light Aspects: "
                + (", ".join(item["name"] for item in aspects) or "None")
            )
            self.output.append(
                "Light Abilities: "
                + (", ".join(item["name"] for item in abilities) or "None")
            )
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
            if item.widget():
                item.widget().deleteLater()

        self.characteristic_value_labels.clear()
        self.characteristic_buttons.clear()
        for column, code in enumerate(CHAR_CODES):
            self.characteristic_grid.addWidget(QLabel(code), 0, column)
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.characteristic_grid.addWidget(value_label, 1, column)
            minus_button = QPushButton("-")
            plus_button = QPushButton("+")
            minus_button.clicked.connect(lambda checked=False, c=code: self.adjust_creation_points(c, -1))
            plus_button.clicked.connect(lambda checked=False, c=code: self.adjust_creation_points(c, 1))
            self.characteristic_grid.addWidget(plus_button, 2, column)
            self.characteristic_grid.addWidget(minus_button, 3, column)
            self.characteristic_value_labels[code] = value_label
            self.characteristic_buttons[code] = (minus_button, plus_button)

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
        use_lns = self.mode_combo.currentText() == "Light & Sky"
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
                    item["name"] for item in connections.get(category, [])
                )
        self.soldier_combo.setVisible(not use_lns)
        self.soldier_label.setVisible(not use_lns)
        self.equipment_button.setVisible(True)
        self.equipment_button.setText(
            "Light Aspects / Abilities" if use_lns else "Equipment Pack"
        )
        for widget in self.core_background_widgets:
            widget.setVisible(not use_lns)
        for widget in self.human_row_widgets:
            widget.setVisible(use_lns)
        for widget in self.guardian_row_widgets:
            widget.setVisible(use_lns)
        self.subclass_combo.setVisible(use_lns)
        self.subclass_label.setVisible(use_lns)
        self.connection_combo.setVisible(use_lns)
        self.connection_label.setVisible(use_lns)

        self.refresh_selection_options()
        self.update_subclasses()
        self._build_outlier_tiles()
        if use_lns:
            self._build_light_power_tiles()
        else:
            self._build_equipment_tiles()

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
            use_lns = self.mode_combo.currentText() == "Light & Sky"
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

    def refresh_core_background_options(self):
        if (
            not hasattr(self, "game_data")
            or getattr(self, "_refreshing_background_options", False)
            or self.mode_combo.currentText() != "Core"
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
            return

        record = self.game_data.get("soldier_type", soldier_type)
        if not record:
            return

        path = record.get("source_path", "")

        # Only Guardian classes have subclasses
        if "guardian_classes_subclasses" in path:
            subclasses = record.get("subclasses", {})
            self.subclass_combo.addItems(list(subclasses.keys()))
        else:
            # No subclasses for UNSC or Human soldier types
            self.subclass_combo.clear()

    # ---------------------------------------------------------
    # Generate character
    # ---------------------------------------------------------
    def generate_character(self):
        name = "Test Character"
        use_lns = self.mode_combo.currentText() == "Light & Sky"
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

        # Show debug log
        self.output.clear()
        for line in char.debug_log:
            self.output.append(line)
        self._update_creation_point_display()
        self.pages.setCurrentWidget(self.creation_page)


# ---------------------------------------------------------
# Run UI
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestGeneratorUI()
    window.show()
    sys.exit(app.exec())
