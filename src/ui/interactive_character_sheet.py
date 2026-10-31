import re
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.game_data import GameData
from src.ui.specialization_page import DelayedTooltipLabel
from src.ui.skill_test_dialog import SkillTestDialog
from src.ui import theme


class InteractiveCharacterSheet(QWidget):
    save_requested = Signal()

    CHARACTERISTICS = (
        ("STR", "Strength"),
        ("TOU", "Toughness"),
        ("AGI", "Agility"),
        ("WFR", "Warfare Range"),
        ("WFM", "Warfare Melee"),
        ("INT", "Intellect"),
        ("PER", "Perception"),
        ("CRG", "Courage"),
        ("CHA", "Charisma"),
        ("LDR", "Leadership"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character_data: dict[str, Any] = {}
        self.note_fields: dict[str, QPlainTextEdit] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QGridLayout()
        title_layout = QVBoxLayout()
        self.name_label = QLabel("Character Sheet")
        self.name_label.setStyleSheet(theme.APP_TITLE)
        self.ruleset_label = QLabel("")
        title_layout.addWidget(self.name_label)
        title_layout.addWidget(self.ruleset_label)
        header.addLayout(title_layout, 0, 0, Qt.AlignmentFlag.AlignLeft)

        experience_controls = QHBoxLayout()
        adjustment_section, adjustment_layout = self._new_section("Adjust XP")
        adjustment_layout.setColumnStretch(0, 1)
        self.xp_adjustment_input = QSpinBox()
        self.xp_adjustment_input.setRange(0, 1_000_000)
        self.xp_adjustment_input.setKeyboardTracking(False)
        self.add_xp_button = QPushButton("Add")
        self.subtract_xp_button = QPushButton("Subtract")
        adjustment_buttons = QHBoxLayout()
        adjustment_buttons.addWidget(self.add_xp_button)
        adjustment_buttons.addWidget(self.subtract_xp_button)
        adjustment_layout.addWidget(self.xp_adjustment_input, 0, 0, 1, 2)
        adjustment_layout.addLayout(adjustment_buttons, 1, 0, 1, 2)
        self.add_xp_button.clicked.connect(
            lambda: self._adjust_experience(self.xp_adjustment_input.value())
        )
        self.subtract_xp_button.clicked.connect(
            lambda: self._adjust_experience(-self.xp_adjustment_input.value())
        )
        experience_controls.addWidget(adjustment_section)
        self.experience_labels = self._add_display_section(
            experience_controls, "Experience", ("Current", "Spent", "Total")
        )
        self.spend_xp_button = QPushButton("Spend XP")
        experience_controls.addWidget(self.spend_xp_button)
        header.addLayout(experience_controls, 0, 1, Qt.AlignmentFlag.AlignCenter)

        header_buttons = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.home_button = QPushButton("Back to Home")
        header_buttons.addWidget(self.save_button)
        header_buttons.addWidget(self.home_button)
        header.addLayout(header_buttons, 0, 2, Qt.AlignmentFlag.AlignRight)
        header.setColumnStretch(0, 1)
        header.setColumnStretch(1, 1)
        header.setColumnStretch(2, 1)
        layout.addLayout(header)

        self.tabs = QTabWidget()
        self.character_tab, self.character_content_layout = (
            self._create_scrollable_tab()
        )
        self.combat_tab, self.combat_content_layout = self._create_scrollable_tab()
        self.tabs.addTab(self.character_tab, "Character")
        self.tabs.addTab(self.combat_tab, "Combat & Notes")
        layout.addWidget(self.tabs)

        self._build_character_tab(self.character_content_layout)
        self._build_combat_tab(self.combat_content_layout)

    def set_character(
        self,
        character: dict[str, Any],
        ruleset: str = "",
        game_data: GameData | None = None,
    ):
        self.character_data = dict(character)
        self.game_data = game_data
        self.name_label.setText(str(character.get("name") or "Unnamed Character"))
        self.ruleset_label.setText(ruleset)

        background = ", ".join(
            str(value)
            for value in (
                character.get("upbringing"),
                character.get("environment"),
                character.get("lifestyle"),
            )
            if value
        ) or "None"
        identity = {
            "Faction": "Not provided",
            "Soldier Type": character.get("soldier_type"),
            "Rank": character.get("rank"),
            "Specialization": self._format_items(
                character.get("specialization_packs")
            ),
            "Race": "Not provided",
            "Background": background,
        }
        for key, label in self.identity_labels.items():
            label.setText(self._display_value(identity[key]))

        characteristics = character.get("characteristics")
        mythic = character.get("mythic_characteristics")
        characteristics = characteristics if isinstance(characteristics, dict) else {}
        mythic = mythic if isinstance(mythic, dict) else {}
        for code, label in self.characteristic_labels.items():
            value = characteristics.get(code, "—")
            label.setText(str(value))
        self._set_characteristic_tooltips(game_data)
        for code, label in self.mythic_characteristic_labels.items():
            value = self._display_value(mythic[code]) if code in mythic else "—"
            label.setText(value)
        self._set_movement_speeds(character, game_data)
        self._set_perceptive_range(character, game_data)
        self._set_carrying_capacity(character, game_data)

        self._set_skill_rows(character.get("skills"), game_data)
        self._set_ability_labels(character.get("abilities"), game_data)
        self.equipment_pack_label.setText(
            self._display_value(character.get("equipment_pack"))
        )
        self.equipment_editor.setPlainText(
            "\n".join(
                str(item)
                for item in self._as_list(character.get("equipment"))
                if item
            )
        )
        self.weapon_label.setText(self._format_items(character.get("weapons")))
        self.armor_label.setText(self._display_value(character.get("armor")))
        self.shield_label.setText("Not provided")
        self._set_light_and_sky_powers(character, ruleset)

        experience = {
            "Current": character.get("experience"),
            "Spent": character.get("experience_spent"),
            "Total": character.get("starting_experience"),
        }
        for key, label in self.experience_labels.items():
            label.setText(self._display_value(experience[key]))
        self._set_luck_values(character, game_data)
        self._set_resource_value("credits", character.get("credits", 0))
        self._set_resource_value("wounds", character.get("wounds", 0))
        self._set_resource_value("fatigue", character.get("fatigue", 0))

        for key, field in self.note_fields.items():
            field.setPlainText(str(character.get(key) or ""))

    def set_save_available(self, available: bool):
        self.save_button.setEnabled(available)

    def character_data_for_save(self):
        for key, field in self.note_fields.items():
            self.character_data[key] = field.toPlainText()
        self.character_data["equipment"] = [
            item.strip()
            for item in self.equipment_editor.toPlainText().splitlines()
            if item.strip()
        ]
        return dict(self.character_data)

    def _build_character_tab(self, layout):
        self.identity_labels = self._add_identity_section(layout)
        self.characteristic_labels = self._add_characteristic_section(layout)
        derived_stats = QHBoxLayout()
        self.movement_labels = self._add_movement_section(derived_stats)
        range_and_capacity = QHBoxLayout()
        self.movement_labels["sight"] = self._add_derived_stat_section(
            range_and_capacity, "Perceptive Range", "Not provided"
        )
        self.carrying_capacity_labels = self._add_carrying_capacity_section(
            range_and_capacity
        )
        range_and_capacity.setStretch(0, 1)
        range_and_capacity.setStretch(1, 1)
        derived_stats.addLayout(range_and_capacity)
        derived_stats.setStretch(0, 1)
        derived_stats.setStretch(1, 1)
        layout.addLayout(derived_stats)

        columns = QHBoxLayout()
        self.skill_table = self._add_skill_section(columns)
        right_column = QVBoxLayout()
        ability_section, self.ability_layout = self._new_section(
            "Abilities and Education"
        )
        right_column.addWidget(ability_section)
        equipment_section, equipment_body = self._new_section("Equipment")
        self.equipment_pack_label = QLabel("None")
        self.equipment_pack_label.setWordWrap(True)
        equipment_body.addWidget(self.equipment_pack_label)
        self.equipment_editor = QPlainTextEdit()
        self.equipment_editor.setPlaceholderText(
            "Add or remove equipment, one item per line..."
        )
        self.equipment_editor.setMinimumHeight(130)
        equipment_body.addWidget(self.equipment_editor)
        right_column.addWidget(equipment_section)
        columns.addLayout(right_column)
        columns.setStretch(0, 1)
        columns.setStretch(1, 1)
        layout.addLayout(columns)

        progress_row = QHBoxLayout()
        resource_layout = QVBoxLayout()
        self.luck_inputs = self._add_luck_inputs(resource_layout)
        self.support_points_label = self._add_value_section(
            resource_layout, "Support Points", "Not provided"
        )
        self.resource_inputs = {}
        self.resource_inputs["credits"] = self._add_resource_input(
            resource_layout, "Credits", "credits"
        )
        progress_row.addLayout(resource_layout)
        layout.addLayout(progress_row)
        layout.addStretch(1)

    def _build_combat_tab(self, layout):
        columns = QHBoxLayout()
        self.weapon_label = self._add_text_section(columns, "Weapons")
        right_column = QVBoxLayout()
        self.armor_label = self._add_value_section(right_column, "Armor")
        self.shield_label = self._add_value_section(right_column, "Shields")
        self.resource_inputs["wounds"] = self._add_resource_input(
            right_column, "Wounds", "wounds"
        )
        self.resource_inputs["fatigue"] = self._add_resource_input(
            right_column, "Fatigue", "fatigue"
        )
        columns.addLayout(right_column)
        columns.setStretch(0, 2)
        columns.setStretch(1, 1)
        layout.addLayout(columns)

        notes_row = QHBoxLayout()
        for key, title in (
            ("medical_notes", "Medical Information"),
            ("character_notes", "Character Information"),
            ("combat_notes", "Armor and Weapons Misc"),
        ):
            section, body = self._new_section(title)
            note = QPlainTextEdit()
            note.setPlaceholderText(f"Add {title.lower()}...")
            note.setMinimumHeight(130)
            body.addWidget(note, 0, 0)
            self.note_fields[key] = note
            notes_row.addWidget(section)
        layout.addLayout(notes_row)

        self.light_and_sky_section, light_and_sky_grid = self._new_section(
            "Light & Sky Powers"
        )
        light_power_fields = (
            ("Light Aspects", "light_aspects_label"),
            ("Light Abilities", "light_abilities_label"),
            ("Light Grenades", "light_grenades_label"),
        )
        for column, (title, label_attribute) in enumerate(light_power_fields):
            section, body = self._new_section(title)
            label = QLabel("None")
            label.setWordWrap(True)
            body.addWidget(label, 0, 0)
            setattr(self, label_attribute, label)
            light_and_sky_grid.addWidget(section, 0, column)
            light_and_sky_grid.setColumnStretch(column, 1)
        self.light_and_sky_section.hide()
        layout.addStretch(1)
        layout.addWidget(self.light_and_sky_section)

    def _set_light_and_sky_powers(self, character, ruleset):
        is_light_and_sky = ruleset == "Light & Sky"
        self.light_and_sky_section.setVisible(is_light_and_sky)
        if not is_light_and_sky:
            return

        self.light_aspects_label.setText(
            self._format_items(character.get("light_aspects"))
        )
        self.light_abilities_label.setText(
            self._format_items(character.get("light_abilities"))
        )
        self.light_grenades_label.setText(
            self._format_items(character.get("light_grenades"))
        )

    def _create_scrollable_tab(self):
        tab = QWidget()
        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(4, 8, 4, 4)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setSpacing(12)
        scroll.setWidget(content)
        tab_layout.addWidget(scroll)
        return tab, content_layout

    def _add_identity_section(self, parent_layout):
        section, grid = self._new_section("Character Identity")
        fields = ("Faction", "Soldier Type", "Rank", "Specialization", "Race", "Background")
        labels = {}
        for index, field in enumerate(fields):
            row, column = divmod(index, 3)
            field_label = QLabel(f"{field}:")
            field_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel("Not provided")
            value_label.setWordWrap(True)
            grid.addWidget(field_label, row * 2, column)
            grid.addWidget(value_label, row * 2 + 1, column)
            labels[field] = value_label
        parent_layout.addWidget(section)
        return labels

    def _add_characteristic_section(self, parent_layout):
        section, grid = self._new_section("Characteristics")
        labels = {}
        self.characteristic_name_labels = {}
        mythic_labels = {}
        for index, (code, name) in enumerate(self.CHARACTERISTICS):
            label = QLabel(f"{name}\n{code}")
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            value = QLabel("—")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value.setMinimumHeight(36)
            value.setStyleSheet(
                "QLabel { background-color: #1b1b1b; border: 1px solid #788f3e; "
                "border-radius: 4px; padding: 4px; font-size: 16px; }"
            )
            grid.addWidget(label, 0, index)
            grid.addWidget(value, 1, index)
            self.characteristic_name_labels[code] = label
            labels[code] = value
            if code in {"STR", "TOU", "AGI"}:
                mythic_title = QLabel("Mythic")
                mythic_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
                mythic_value = QLabel("—")
                mythic_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
                mythic_value.setMinimumHeight(28)
                mythic_value.setStyleSheet(
                    "QLabel { background-color: #1b1b1b; border: 1px solid #788f3e; "
                    "border-radius: 4px; padding: 2px; }"
                )
                grid.addWidget(mythic_title, 2, index)
                grid.addWidget(mythic_value, 3, index)
                mythic_labels[code] = mythic_value
        parent_layout.addWidget(section)
        self.mythic_characteristic_labels = mythic_labels
        return labels

    def _set_characteristic_tooltips(self, game_data: GameData | None):
        document = (
            game_data.get("characteristics", "characteristics")
            if game_data is not None
            else None
        )
        records = (
            document.get("characteristics", [])
            if isinstance(document, dict)
            else []
        )
        descriptions = {
            record["id"].upper(): record.get("description", "")
            for record in records
            if isinstance(record, dict)
            and isinstance(record.get("id"), str)
        }
        for code, label in self.characteristic_name_labels.items():
            description = descriptions.get(code, "")
            label.setToolTip(description)
            self.characteristic_labels[code].setToolTip(description)

    def _set_ability_labels(self, abilities, game_data: GameData | None):
        while self.ability_layout.count():
            item = self.ability_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        descriptions = {}
        if game_data is not None:
            for document in game_data.families.get("light_abilities", {}).values():
                for record in document.get("abilities", []):
                    if not isinstance(record, dict):
                        continue
                    name = record.get("name")
                    description = record.get("description")
                    if isinstance(name, str) and isinstance(description, str):
                        descriptions[name.casefold()] = description

        ability_names = [
            str(name)
            for name in self._as_list(abilities)
            if name
        ]
        if not ability_names:
            self.ability_layout.addWidget(QLabel("None"))
            return

        for name in ability_names:
            label = DelayedTooltipLabel(
                name,
                descriptions.get(name.casefold(), ""),
            )
            label.setWordWrap(True)
            self.ability_layout.addWidget(label)

    def _add_movement_section(self, parent_layout):
        section, grid = self._new_section("Movement")
        labels = {}
        for column, (key, title) in enumerate(
            (
                ("half", "Half"),
                ("full", "Full"),
                ("charge", "Charge"),
                ("run", "Run"),
                ("sprint", "Sprint"),
            )
        ):
            title_label = QLabel(title)
            title_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel("Not provided")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(title_label, 0, column)
            grid.addWidget(value_label, 1, column)
            labels[key] = value_label
        modifier_label = QLabel("Agility Modifier: Not provided")
        grid.addWidget(modifier_label, 2, 0, 1, 5)
        labels["agility_modifier"] = modifier_label
        parent_layout.addWidget(section)
        return labels

    def _add_derived_stat_section(self, parent_layout, title, initial_value):
        section, grid = self._new_section(title)
        value_label = QLabel(initial_value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        grid.addWidget(value_label, 0, 0)
        parent_layout.addWidget(section)
        return value_label

    def _add_carrying_capacity_section(self, parent_layout):
        section, grid = self._new_section("Carrying Capacity")
        labels = {}
        for column, key in enumerate(("carry", "lift", "push")):
            title = QLabel(key.title())
            title.setStyleSheet("font-weight: bold;")
            value = QLabel("Not provided")
            value.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(title, 0, column)
            grid.addWidget(value, 1, column)
            labels[key] = value
        parent_layout.addWidget(section)
        return labels

    def _set_carrying_capacity(
        self, character: dict[str, Any], game_data: GameData | None
    ):
        unavailable = "Not available"
        if game_data is None:
            self._display_unavailable_carrying_capacity(unavailable)
            return

        encumbrance_doc = game_data.get("encumbrance", "encumbrance")
        encumbrance_rules = (
            encumbrance_doc.get("encumbrance")
            if isinstance(encumbrance_doc, dict)
            else None
        )
        mythic_doc = game_data.get(
            "mythic_characteristics", "mythic_characteristics"
        )
        mythic_rules = mythic_doc.get("mythic") if isinstance(mythic_doc, dict) else None
        strength_rule = (
            mythic_rules.get("strength") if isinstance(mythic_rules, dict) else None
        )
        toughness_rule = (
            mythic_rules.get("toughness") if isinstance(mythic_rules, dict) else None
        )
        if (
            not isinstance(encumbrance_rules, dict)
            or not isinstance(strength_rule, dict)
            or not isinstance(toughness_rule, dict)
        ):
            self._display_unavailable_carrying_capacity(unavailable)
            return

        carry_formula = encumbrance_rules.get("carry_weight")
        if not isinstance(carry_formula, str) or re.fullmatch(
            r"\s*half\s+of\s+strength\s*\+\s*toughness\s*",
            carry_formula,
            re.IGNORECASE,
        ) is None:
            self._display_unavailable_carrying_capacity(unavailable)
            return

        lift_multiplier = self._formula_multiplier(
            encumbrance_rules.get("lift_weight"), "Carry Weight"
        )
        push_multiplier = self._formula_multiplier(
            encumbrance_rules.get("push_weight"), "Carry Weight"
        )
        strength_bonus_multiplier = self._formula_multiplier(
            strength_rule.get("carry_weight_bonus"), "X"
        )
        toughness_bonus_multiplier = self._formula_multiplier(
            toughness_rule.get("carry_weight_bonus"), "X"
        )
        characteristics = character.get("characteristics")
        mythic_characteristics = character.get("mythic_characteristics")
        if (
            lift_multiplier is None
            or push_multiplier is None
            or strength_bonus_multiplier is None
            or toughness_bonus_multiplier is None
            or not isinstance(characteristics, dict)
        ):
            self._display_unavailable_carrying_capacity(unavailable)
            return

        strength = self._parse_integer(characteristics.get("STR"))
        toughness = self._parse_integer(characteristics.get("TOU"))
        mythic_strength = (
            self._parse_integer(mythic_characteristics.get("STR", 0))
            if isinstance(mythic_characteristics, dict)
            else 0
        )
        mythic_toughness = (
            self._parse_integer(mythic_characteristics.get("TOU", 0))
            if isinstance(mythic_characteristics, dict)
            else 0
        )
        if (
            strength is None
            or toughness is None
            or mythic_strength is None
            or mythic_toughness is None
        ):
            self._display_unavailable_carrying_capacity(unavailable)
            return

        strength_value = strength + mythic_strength * strength_bonus_multiplier
        toughness_value = toughness + mythic_toughness * toughness_bonus_multiplier
        soldier_record = self._soldier_type_record(character, game_data)
        traits = (
            soldier_record.get("traits", [])
            if isinstance(soldier_record, dict)
            else []
        )
        spartan_doubling = any(
            isinstance(trait, dict)
            and trait.get("name") == "Carry Weight"
            and isinstance(trait.get("effect"), str)
            and "Doubles Strength and Toughness" in trait["effect"]
            for trait in traits
        )
        if spartan_doubling:
            strength_value *= 2
            toughness_value *= 2

        selected_outliers = self._selected_outlier_effects(character, game_data)
        strongman_effect = selected_outliers.get("Strongman", "")
        selected_outlier_names = self._as_list(character.get("outliers"))
        if "Strongman" in selected_outlier_names and not strongman_effect:
            self._display_unavailable_carrying_capacity(unavailable)
            return
        strongman = (
            isinstance(strongman_effect, str)
            and "no halving" in strongman_effect.lower()
        )
        strong_back = self._strong_back_selected(character, game_data)
        if strong_back is None:
            self._display_unavailable_carrying_capacity(unavailable)
            return

        carry_basis = strength_value + toughness_value
        lift_push_toughness = toughness_value * (2 if strong_back else 1)
        lift_push_basis = strength_value + lift_push_toughness
        if not strongman:
            carry_basis /= 2
            lift_push_basis /= 2

        values = {
            "carry": carry_basis,
            "lift": lift_push_basis * lift_multiplier,
            "push": lift_push_basis * push_multiplier,
        }
        for key, value in values.items():
            self.carrying_capacity_labels[key].setText(f"{value:g}")

    def _display_unavailable_carrying_capacity(self, message: str):
        for label in self.carrying_capacity_labels.values():
            label.setText(message)

    @staticmethod
    def _formula_multiplier(formula, subject):
        if not isinstance(formula, str):
            return None
        match = re.fullmatch(
            rf"\s*{re.escape(subject)}\s*[*×]\s*(\d+)\s*",
            formula,
            re.IGNORECASE,
        )
        if match is None:
            return None
        return int(match.group(1))

    @staticmethod
    def _soldier_type_record(character: dict[str, Any], game_data: GameData):
        soldier_type = character.get("soldier_type")
        if not isinstance(soldier_type, str):
            return None
        return next(
            (
                record
                for record in game_data.families.get("soldier_type", {}).values()
                if isinstance(record, dict) and record.get("name") == soldier_type
            ),
            None,
        )

    @staticmethod
    def _selected_outlier_effects(
        character: dict[str, Any], game_data: GameData
    ) -> dict[str, str]:
        selected_names = {
            name
            for name in InteractiveCharacterSheet._as_list(
                character.get("outliers")
            )
            if isinstance(name, str)
        }
        effects = {}
        for document in game_data.families.get("outliers", {}).values():
            outlier_data = (
                document.get("outliers") if isinstance(document, dict) else None
            )
            outliers = (
                outlier_data.get("list") if isinstance(outlier_data, dict) else None
            )
            if not isinstance(outliers, list):
                continue
            for outlier in outliers:
                if (
                    isinstance(outlier, dict)
                    and outlier.get("name") in selected_names
                    and isinstance(outlier.get("effect"), str)
                ):
                    effects[outlier["name"]] = outlier["effect"]
        return effects

    @staticmethod
    def _strong_back_selected(
        character: dict[str, Any], game_data: GameData
    ) -> bool | None:
        selected_abilities = {
            name
            for name in InteractiveCharacterSheet._as_list(
                character.get("abilities")
            )
            if isinstance(name, str)
        }
        if "Strong Back" not in selected_abilities:
            return False

        ability_doc = game_data.get("light_abilities", "abilities")
        ability_entries = (
            ability_doc.get("abilities") if isinstance(ability_doc, dict) else None
        )
        if not isinstance(ability_entries, list):
            return None
        for ability in ability_entries:
            if not isinstance(ability, dict) or ability.get("name") != "Strong Back":
                continue
            description = ability.get("description")
            if not isinstance(description, str):
                return None
            return (
                "doubles their Toughness Characteristic for figuring Lift and Push"
                in description
            )
        return None

    def _set_movement_speeds(
        self, character: dict[str, Any], game_data: GameData | None
    ):
        unavailable = "Not available"
        if game_data is None:
            self._display_unavailable_movement(unavailable)
            return

        movement_doc = game_data.get("movement_speeds", "movement_speeds")
        modifier_doc = game_data.get(
            "characteristic_modifiers", "characteristic_modifiers"
        )
        mythic_doc = game_data.get(
            "mythic_characteristics", "mythic_characteristics"
        )
        movement_rules = (
            movement_doc.get("movement_speeds")
            if isinstance(movement_doc, dict)
            else None
        )
        modifier_rules = (
            modifier_doc.get("modifier_rules")
            if isinstance(modifier_doc, dict)
            else None
        )
        mythic_rules = mythic_doc.get("mythic") if isinstance(mythic_doc, dict) else None
        agility_rule = (
            mythic_rules.get("agility")
            if isinstance(mythic_rules, dict)
            else None
        )
        if (
            not isinstance(movement_rules, dict)
            or not isinstance(modifier_rules, dict)
            or not isinstance(agility_rule, dict)
            or agility_rule.get("movement_bonus") != "modifier + X"
        ):
            self._display_unavailable_movement(unavailable)
            return

        characteristics = character.get("characteristics")
        mythic_characteristics = character.get("mythic_characteristics")
        if not isinstance(characteristics, dict):
            self._display_unavailable_movement(unavailable)
            return
        agility = self._parse_integer(characteristics.get("AGI"))
        mythic_agility = (
            self._parse_integer(mythic_characteristics.get("AGI", 0))
            if isinstance(mythic_characteristics, dict)
            else 0
        )
        if agility is None or mythic_agility is None:
            self._display_unavailable_movement(unavailable)
            return

        modifier_key = "above_100" if agility >= 100 else "below_100"
        if modifier_rules.get(modifier_key) != "floor(value / 10)":
            self._display_unavailable_movement(unavailable)
            return
        agility_modifier = agility // 10 + mythic_agility
        aspect_bonus = self._movement_aspect_bonus(character, game_data)
        if aspect_bonus is None:
            self._display_unavailable_movement(unavailable)
            return
        agility_modifier += aspect_bonus
        self.movement_labels["agility_modifier"].setText(
            f"Agility Modifier: {agility_modifier}"
        )

        movement_table = movement_rules.get("table")
        if not isinstance(movement_table, list):
            self._display_unavailable_movement(unavailable)
            return
        movement = next(
            (
                row
                for row in movement_table
                if isinstance(row, dict) and row.get("mod") == agility_modifier
            ),
            None,
        )
        if movement is None:
            self._display_unavailable_movement(
                f"No movement entry for modifier {agility_modifier}"
            )
            return

        for key in ("half", "full", "charge", "run", "sprint"):
            speed = movement.get(key)
            if isinstance(speed, (int, float)):
                self.movement_labels[key].setText(f"{speed:g} m")
            else:
                self.movement_labels[key].setText(unavailable)

    def _set_perceptive_range(
        self, character: dict[str, Any], game_data: GameData | None
    ):
        label = self.movement_labels["sight"]
        if game_data is None:
            label.setText("Not available")
            return

        range_doc = game_data.get("perceptive_range", "perceptive_range")
        range_rules = (
            range_doc.get("perceptive_range")
            if isinstance(range_doc, dict)
            else None
        )
        base_formula = (
            range_rules.get("base_formula")
            if isinstance(range_rules, dict)
            else None
        )
        formula_match = (
            re.fullmatch(r"\s*perception\s*\*\s*(\d+)\s*", base_formula)
            if isinstance(base_formula, str)
            else None
        )
        characteristics = character.get("characteristics")
        perception = (
            self._parse_integer(characteristics.get("PER"))
            if isinstance(characteristics, dict)
            else None
        )
        if formula_match is None or perception is None:
            label.setText("Not available")
            return

        multiplier = int(formula_match.group(1))
        selected_outliers = {
            name
            for name in self._as_list(character.get("outliers"))
            if isinstance(name, str)
        }
        outlier_documents = game_data.families.get("outliers", {})
        for document in outlier_documents.values():
            outlier_data = (
                document.get("outliers") if isinstance(document, dict) else None
            )
            outlier_list = (
                outlier_data.get("list")
                if isinstance(outlier_data, dict)
                else None
            )
            if not isinstance(outlier_list, list):
                continue
            for outlier in outlier_list:
                if (
                    not isinstance(outlier, dict)
                    or outlier.get("name") not in selected_outliers
                ):
                    continue
                effect = outlier.get("effect")
                if not isinstance(effect, str):
                    continue
                bonus_match = re.search(
                    r"Perceptive Range multiplier increases by (\d+)",
                    effect,
                    re.IGNORECASE,
                )
                if bonus_match is not None:
                    multiplier += int(bonus_match.group(1))

        label.setText(f"{perception * multiplier} m")

    @classmethod
    def _movement_aspect_bonus(
        cls, character: dict[str, Any], game_data: GameData
    ) -> int | None:
        raw_selected_aspects = cls._as_list(character.get("light_aspects"))
        if not all(isinstance(name, str) for name in raw_selected_aspects):
            return None
        selected_aspects = set(raw_selected_aspects)
        if not selected_aspects:
            return 0

        aspect_doc = game_data.get("light_aspects", "light_aspects")
        aspects_by_connection = (
            aspect_doc.get("light_aspects") if isinstance(aspect_doc, dict) else None
        )
        if not isinstance(aspects_by_connection, dict):
            return None

        found_aspects = set()
        movement_bonus = 0
        for aspects in aspects_by_connection.values():
            if not isinstance(aspects, list):
                continue
            for aspect in aspects:
                if not isinstance(aspect, dict):
                    continue
                name = aspect.get("name")
                if name not in selected_aspects:
                    continue
                found_aspects.add(name)
                description = aspect.get("description", "")
                if isinstance(description, str) and (
                    "Agility Modifier is increased by 1 when figuring Movement Speeds."
                    in description
                ):
                    movement_bonus += 1

        if found_aspects != selected_aspects:
            return None
        return movement_bonus

    def _display_unavailable_movement(self, message: str):
        for key in ("half", "full", "charge", "run", "sprint"):
            self.movement_labels[key].setText(message)
        self.movement_labels["agility_modifier"].setText(
            f"Agility Modifier: {message}"
        )

    def _add_skill_section(self, parent_layout):
        section, body = self._new_section("Skills")
        table = QTableWidget(0, 4)
        table.setHorizontalHeaderLabels(("Skill", "Trained", "+10", "+20"))
        table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
        for column in range(1, 4):
            table.horizontalHeader().setSectionResizeMode(
                column, QHeaderView.ResizeMode.ResizeToContents
            )
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        table.cellClicked.connect(self._open_skill_test)
        body.addWidget(table, 0, 0)
        parent_layout.addWidget(section)
        return table

    def _set_skill_rows(self, skills, game_data):
        self.skill_table.setRowCount(0)
        trained_skills = skills if isinstance(skills, dict) else {}
        skills_document = (
            game_data.get("skills", "skills") if game_data is not None else None
        )
        skill_records = (
            skills_document.get("skills", [])
            if isinstance(skills_document, dict)
            else []
        )
        skill_names = [
            record["name"]
            for record in skill_records
            if isinstance(record, dict)
            and isinstance(record.get("name"), str)
        ]
        skill_names.extend(
            name
            for name in trained_skills
            if isinstance(name, str) and name not in skill_names
        )

        for name in skill_names:
            trained = name in trained_skills
            value = (
                self._integer_value(trained_skills[name]) if trained else 0
            )
            row = self.skill_table.rowCount()
            self.skill_table.insertRow(row)
            self.skill_table.setItem(row, 0, QTableWidgetItem(name))
            for column, selected in enumerate(
                (trained, trained and value >= 10, trained and value >= 20),
                1,
            ):
                checkbox = QCheckBox()
                checkbox.setChecked(selected)
                checkbox.setEnabled(False)
                checkbox.setStyleSheet("QCheckBox { margin-left: 8px; }")
                cell = QWidget()
                cell_layout = QHBoxLayout(cell)
                cell_layout.setContentsMargins(0, 0, 0, 0)
                cell_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                cell_layout.addWidget(checkbox)
                self.skill_table.setCellWidget(row, column, cell)
        self.skill_table.resizeRowsToContents()
        table_height = (
            self.skill_table.horizontalHeader().height()
            + sum(
                self.skill_table.rowHeight(row)
                for row in range(self.skill_table.rowCount())
            )
            + 2 * self.skill_table.frameWidth()
        )
        self.skill_table.setFixedHeight(table_height)

    def _open_skill_test(self, row, column):
        skill_item = self.skill_table.item(row, 0)
        if skill_item is None:
            return

        skill_name = skill_item.text()
        skills_document = (
            self.game_data.get("skills", "skills")
            if self.game_data is not None
            else None
        )
        skill_records = (
            skills_document.get("skills", [])
            if isinstance(skills_document, dict)
            else []
        )
        skill_record = next(
            (
                record
                for record in skill_records
                if isinstance(record, dict)
                and record.get("name") == skill_name
            ),
            {},
        )

        characteristics_document = (
            self.game_data.get("characteristics", "characteristics")
            if self.game_data is not None
            else None
        )
        characteristic_records = (
            characteristics_document.get("characteristics", [])
            if isinstance(characteristics_document, dict)
            else []
        )
        records_by_name = {
            record["name"].casefold(): record
            for record in characteristic_records
            if isinstance(record, dict)
            and isinstance(record.get("name"), str)
            and isinstance(record.get("id"), str)
        }
        records_by_code = {
            record["id"].upper(): record
            for record in characteristic_records
            if isinstance(record, dict)
            and isinstance(record.get("name"), str)
            and isinstance(record.get("id"), str)
        }
        characteristic_values = self.character_data.get("characteristics")
        characteristic_values = (
            characteristic_values
            if isinstance(characteristic_values, dict)
            else {}
        )

        linked_characteristics = skill_record.get("characteristics", [])
        if not isinstance(linked_characteristics, list):
            linked_characteristics = []
        characteristic_options = []
        for linked_name in linked_characteristics:
            if not isinstance(linked_name, str):
                continue
            record = records_by_name.get(linked_name.casefold())
            if record is None:
                record = records_by_code.get(linked_name.upper())
            if record is None:
                continue
            code = record["id"].upper()
            characteristic_value = self._parse_integer(
                characteristic_values.get(code)
            )
            if characteristic_value is None:
                characteristic_value = 0
            characteristic_options.append(
                (record["name"], code, characteristic_value)
            )

        if not characteristic_options:
            characteristic_options = [
                (
                    record["name"],
                    code,
                    self._parse_integer(characteristic_values.get(code)) or 0,
                )
                for code, record in records_by_code.items()
            ]

        raw_skill_value = self.character_data.get("skills")
        is_trained = isinstance(raw_skill_value, dict) and skill_name in raw_skill_value
        skill_level = (
            self._integer_value(raw_skill_value[skill_name]) if is_trained else -10
        )
        skill_level = max(-10, min(20, skill_level))

        difficulty_modifiers = (
            skills_document.get("difficulty_modifiers", [])
            if isinstance(skills_document, dict)
            else []
        )
        difficulty_options = [
            (entry["difficulty"], entry["modifier"])
            for entry in difficulty_modifiers
            if isinstance(entry, dict)
            and isinstance(entry.get("difficulty"), str)
            and isinstance(entry.get("modifier"), int)
        ]
        if not characteristic_options or not difficulty_options:
            return

        dialog = SkillTestDialog(
            skill_name,
            characteristic_options,
            skill_level,
            difficulty_options,
            parent=self,
        )
        dialog.exec()

    def _add_display_section(self, parent_layout, title, fields):
        section, grid = self._new_section(title)
        labels = {}
        for column, field in enumerate(fields):
            field_label = QLabel(field)
            field_label.setStyleSheet("font-weight: bold;")
            value_label = QLabel("—")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            grid.addWidget(field_label, 0, column)
            grid.addWidget(value_label, 1, column)
            labels[field] = value_label
        parent_layout.addWidget(section)
        return labels

    def _adjust_experience(self, adjustment):
        current = max(
            0, self._parse_integer(self.character_data.get("experience")) or 0
        )
        spent = max(
            0,
            self._parse_integer(self.character_data.get("experience_spent"))
            or 0,
        )
        current = max(0, current + adjustment)
        total = current + spent
        self.character_data["experience"] = current
        self.character_data["starting_experience"] = total
        self.experience_labels["Current"].setText(str(current))
        self.experience_labels["Total"].setText(str(total))

    def _add_resource_input(self, parent_layout, title, key):
        section, grid = self._new_section(title)
        spin_box = QSpinBox()
        spin_box.setRange(0, 1_000_000)
        spin_box.valueChanged.connect(
            lambda value, field=key: self.character_data.__setitem__(field, value)
        )
        grid.addWidget(spin_box, 0, 0)
        parent_layout.addWidget(section)
        return spin_box

    def _add_luck_inputs(self, parent_layout):
        section, grid = self._new_section("Luck")
        inputs = {}
        for column, (key, title) in enumerate(
            (("available", "Available"), ("total", "Total"))
        ):
            field_label = QLabel(title)
            field_label.setStyleSheet("font-weight: bold;")
            spin_box = QSpinBox()
            spin_box.setRange(0, 1_000_000)
            if key == "available":
                spin_box.setMaximum(0)
            grid.addWidget(field_label, 0, column)
            grid.addWidget(spin_box, 1, column)
            inputs[key] = spin_box
        inputs["available"].valueChanged.connect(
            lambda value: self.character_data.__setitem__("luck_available", value)
        )
        inputs["total"].valueChanged.connect(self._set_luck_total)
        parent_layout.addWidget(section)
        return inputs

    def _set_luck_total(self, value):
        self.character_data["luck_total"] = value
        available_input = self.luck_inputs["available"]
        available_input.setMaximum(value)
        available_input.setValue(min(available_input.value(), value))

    def _set_luck_values(
        self, character: dict[str, Any], game_data: GameData | None
    ):
        total = self._parse_integer(character.get("luck_total"))
        if total is None:
            total = self._tier_luck(character, game_data)
        total_known = total is not None
        total = max(0, total or 0)

        available = self._parse_integer(character.get("luck_available"))
        legacy_burned = self._parse_integer(character.get("luck_burned"))
        if available is None:
            if legacy_burned is not None and total_known:
                total = max(0, total - max(0, legacy_burned))
                available = total + max(0, legacy_burned)
            else:
                available = total
        available = min(total, max(0, available))

        self.character_data.pop("luck_burned", None)
        self.character_data["luck_total"] = total
        self.character_data["luck_available"] = available
        total_input = self.luck_inputs["total"]
        available_input = self.luck_inputs["available"]
        total_input.setValue(total)
        available_input.setMaximum(total)
        available_input.setValue(available)

    @classmethod
    def _tier_luck(
        cls, character: dict[str, Any], game_data: GameData | None
    ) -> int | None:
        if game_data is None:
            return None
        experience_tier = cls._parse_integer(character.get("experience_tier"))
        if experience_tier is None:
            return None

        document = game_data.get("experience_tiers", "experience_tiers")
        experience_data = (
            document.get("experience_tiers") if isinstance(document, dict) else None
        )
        tiers = (
            experience_data.get("tiers")
            if isinstance(experience_data, dict)
            else None
        )
        if not isinstance(tiers, list):
            return None
        for tier in tiers:
            if not isinstance(tier, dict):
                continue
            if cls._parse_integer(tier.get("tier")) == experience_tier:
                return cls._parse_integer(tier.get("luck"))
        return None

    def _set_resource_value(self, key, value):
        spin_box = self.resource_inputs[key]
        spin_box.setValue(self._integer_value(value))
        self.character_data[key] = spin_box.value()

    def _add_text_section(self, parent_layout, title):
        section, body = self._new_section(title)
        label = QLabel("None")
        label.setWordWrap(True)
        body.addWidget(label)
        parent_layout.addWidget(section)
        return label

    def _add_value_section(self, parent_layout, title, value="Not provided"):
        section, grid = self._new_section(title)
        label = QLabel(value)
        label.setWordWrap(True)
        grid.addWidget(label, 0, 0)
        parent_layout.addWidget(section)
        return label

    @staticmethod
    def _new_section(title):
        section = QFrame()
        section.setFrameShape(QFrame.Shape.StyledPanel)
        section.setStyleSheet(
            "QFrame { background-color: #242424; border: 1px solid #526b28; "
            "border-radius: 6px; }"
        )
        layout = QVBoxLayout(section)
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 17px; font-weight: bold;")
        layout.addWidget(title_label)
        grid = QGridLayout()
        layout.addLayout(grid)
        return section, grid

    @staticmethod
    def _format_items(values):
        if not isinstance(values, (list, tuple)):
            return InteractiveCharacterSheet._display_value(values)
        items = [str(value) for value in values if value]
        return "\n".join(items) or "None"

    @staticmethod
    def _as_list(value):
        if isinstance(value, (list, tuple)):
            return value
        return [value] if value else []

    @staticmethod
    def _display_value(value):
        return str(value) if value not in (None, "") else "None"

    @staticmethod
    def _integer_value(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _parse_integer(value):
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
