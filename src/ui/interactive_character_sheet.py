import html
import random
import re
from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMessageBox,
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
from src.models import worn_armor
from src.models.derived_stats import max_wounds
from src.models.starting_armor import format_bonus
from src.models import attack, damage_resistance, energy_shields, throwing
from src.models.light_loadout import LightLoadout
from src.models import outliers as outlier_rules
from src.models.xp_shop import XpShop
from src.models.equipment_packs import (
    armor_index,
    armor_summary,
    armory_index,
    weapon_summary,
)
from src.loot import character_loot
from src.loot.generator import LootDataMissing, LootGenerator
from src.ui.loot_dialog import LootDialog
from src.ui.specialization_page import DelayedTooltipLabel
from src.ui.skill_test_dialog import SkillTestDialog
from src.ui.attack_roll_dialog import AttackRollDialog
from src.ui.light_and_sky_page import LightAndSkyPage
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
        self.game_data: GameData | None = None
        self.dice_rng = random.Random()  # tests can seed this
        self.ruleset = ""
        self.note_fields: dict[str, QPlainTextEdit] = {}

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        # Styled here rather than on self, so dialogs parented to the sheet
        # keep their own look.
        page = QWidget()
        page.setObjectName("sheetPage")
        page.setStyleSheet(theme.SHEET_STYLE)
        outer.addWidget(page)
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self._build_masthead())

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.character_tab, self.character_content_layout = (
            self._create_scrollable_tab()
        )
        self.combat_tab, self.combat_content_layout = self._create_scrollable_tab()
        self.notes_tab, self.notes_content_layout = self._create_scrollable_tab()
        # Shown only for Light & Sky characters (see _set_light_and_sky_powers)
        self.light_tab, light_content_layout = self._create_scrollable_tab()
        self.light_page = LightAndSkyPage()
        self.light_page.loadout_changed.connect(self._refresh_armor_effects)
        self.light_page.unlock_requested.connect(self.spend_xp_button.click)
        light_content_layout.addWidget(self.light_page)
        self.tabs.addTab(self.character_tab, "Character")
        self.tabs.addTab(self.combat_tab, "Combat")
        self.tabs.addTab(self.notes_tab, "Notes")
        layout.addWidget(self.tabs)

        self._build_character_tab(self.character_content_layout)
        self._build_combat_tab(self.combat_content_layout)
        self._build_notes_tab(self.notes_content_layout)

    def _build_masthead(self):
        masthead = QWidget()
        masthead.setObjectName("sheetMasthead")
        layout = QVBoxLayout(masthead)
        layout.setContentsMargins(24, 14, 24, 12)
        layout.setSpacing(8)

        title_row = QHBoxLayout()
        title_text = QVBoxLayout()
        title_text.setSpacing(0)
        self.name_label = self._role_label("Character Sheet", "sheet-name")
        self.ruleset_label = self._role_label("", "sheet-subtitle")
        title_text.addWidget(self.name_label)
        title_text.addWidget(self.ruleset_label)
        title_row.addLayout(title_text, 1)
        self.loot_button = QPushButton("Light && Sky Loot")
        self.loot_button.setToolTip(
            "Roll random Light & Sky weapons and armor for this character."
        )
        self.loot_button.clicked.connect(self.open_loot_dialog)
        self.loot_button.hide()
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_requested.emit)
        self.home_button = QPushButton("Back to Home")
        for button in (self.loot_button, self.save_button, self.home_button):
            title_row.addWidget(button, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(title_row)

        xp_row = QHBoxLayout()
        xp_row.setSpacing(18)
        self.experience_labels = {}
        for field, caption in (
            ("Current", "XP AVAILABLE"),
            ("Spent", "XP SPENT"),
            ("Total", "XP TOTAL"),
        ):
            readout = QVBoxLayout()
            readout.setSpacing(0)
            readout.addWidget(self._role_label(caption, "caption"))
            value = self._role_label("—", "xp-value")
            readout.addWidget(value)
            xp_row.addLayout(readout)
            self.experience_labels[field] = value
        self.spend_xp_button = QPushButton("Spend XP")
        self.spend_xp_button.setProperty("role", "primary")
        self.spend_xp_button.setToolTip(
            "Open the XP Shop to buy Characteristics, Skills, Abilities, "
            "Educations, Training, Luck, Wounds and (Light & Sky) Light powers."
        )
        xp_row.addWidget(self.spend_xp_button)
        xp_row.addStretch(1)
        xp_row.addWidget(self._role_label("ADJUST XP", "caption"))
        self.xp_adjustment_input = QSpinBox()
        self.xp_adjustment_input.setRange(0, 1_000_000)
        self.xp_adjustment_input.setKeyboardTracking(False)
        self.xp_adjustment_input.setMinimumWidth(90)
        self.add_xp_button = QPushButton("Add")
        self.subtract_xp_button = QPushButton("Subtract")
        self.add_xp_button.clicked.connect(
            lambda: self._adjust_experience(self.xp_adjustment_input.value())
        )
        self.subtract_xp_button.clicked.connect(
            lambda: self._adjust_experience(-self.xp_adjustment_input.value())
        )
        adjust = QHBoxLayout()
        adjust.setSpacing(6)
        for widget in (self.xp_adjustment_input, self.add_xp_button, self.subtract_xp_button):
            adjust.addWidget(widget)
        xp_row.addLayout(adjust)
        layout.addLayout(xp_row)
        return masthead

    def set_character(
        self,
        character: dict[str, Any],
        ruleset: str = "",
        game_data: GameData | None = None,
    ):
        self.character_data = dict(character)
        self.game_data = game_data
        self.ruleset = ruleset
        if ruleset == "Light & Sky":
            # Settle which Aspects are slotted before movement is worked out
            LightLoadout(self.character_data, game_data, ruleset).loadout()
        self.loot_button.setVisible(ruleset == "Light & Sky")
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
            "Faction": "—",
            "Soldier Type": character.get("soldier_type"),
            "Rank": character.get("rank"),
            "Specialization": self._format_items(
                character.get("specialization_packs")
            ),
            "Race": "—",
            "Background": background,
        }
        for key, label in self.identity_labels.items():
            label.setText(self._display_value(identity[key]))

        self._set_characteristic_tooltips(game_data)
        saved_other = character.get("damage_resistance_other")
        saved_other = saved_other if isinstance(saved_other, dict) else {}
        for slot, box in self.dr_other_inputs.items():
            box.blockSignals(True)
            box.setValue(self._integer_value(saved_other.get(slot, 0)))
            box.blockSignals(False)
        self._load_energy_shield_inputs(character)
        has_armor = bool(character.get("armor"))
        self.armor_equipped_checkbox.blockSignals(True)
        self.armor_equipped_checkbox.setEnabled(has_armor)
        self.armor_equipped_checkbox.setChecked(worn_armor.is_equipped(character))
        self.armor_equipped_checkbox.blockSignals(False)
        if has_armor:
            self.character_data["armor_equipped"] = worn_armor.is_equipped(character)
        self._refresh_armor_effects()

        self._set_skill_rows(character.get("skills"), game_data)
        self._set_ability_labels(character.get("abilities"), game_data)
        self._add_learned_labels(character)
        self.equipment_pack_label.setText(
            self._display_value(character.get("equipment_pack")).replace("_", " ").title()
        )
        self.equipment_editor.setPlainText(
            "\n".join(
                str(item)
                for item in self._as_list(character.get("equipment"))
                if item
            )
        )
        armory = armory_index(game_data) if game_data else {}
        weapons = self._as_list(character.get("weapons"))
        self.weapon_label.setText(
            self._summary_html([weapon_summary(weapon, armory) for weapon in weapons])
        )
        self.weapon_label.setToolTip(
            "\n\n".join(
                f"{weapon.get('name')}\n{character_loot.perk_descriptions(weapon['loot'])}"
                for weapon in weapons
                if isinstance(weapon, dict)
                and isinstance(weapon.get("loot"), dict)
                and character_loot.perk_descriptions(weapon["loot"])
            )
        )
        armors = armor_index(game_data) if game_data else {}
        loot_armor = character_loot.worn_loot_armor(character)
        if loot_armor:
            armor_lines = character_loot.armor_sheet_lines(loot_armor)
            self.armor_label.setToolTip(character_loot.perk_descriptions(loot_armor))
        else:
            armor_lines = [armor_summary(character.get("armor"), armors)]
            self.armor_label.setToolTip("")
        variant = character.get("armor_variant")
        if isinstance(variant, dict) and variant.get("name"):
            armor_lines.append(
                f"Variant: {variant['name']} ({variant.get('generation', '')})"
            )
        bonus = format_bonus(character.get("armor_bonus"))
        if bonus:
            armor_lines.append(f"While worn: {bonus}")
        self.armor_label.setText(
            self._summary_html(
                ["\n".join(line for line in armor_lines if line)] if any(armor_lines) else []
            )
        )
        self._populate_attack_weapons()
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
        self._set_resource_value("support_points", character.get("support_points", 0))
        advocate = outlier_rules.support_points(game_data, character)
        self.resource_inputs["support_points"].setToolTip(
            "Support Points from your Rank (set by the GM)"
            + (
                f", including +{advocate} from Advocate at creation. "
                f"Advocate also adds +{advocate} each time you are rewarded after a mission."
                if advocate
                else "."
            )
        )
        self._set_outlier_section(character, game_data)
        self._refresh_outlier_readouts()

        for key, field in self.note_fields.items():
            field.setPlainText(str(character.get(key) or ""))

    # ---------------------------------------------------------
    # Light & Sky loot
    # ---------------------------------------------------------
    def open_loot_dialog(self):
        try:
            generator = LootGenerator(getattr(self, "game_data", None))
        except LootDataMissing as error:
            QMessageBox.warning(self, "Loot Unavailable", str(error))
            return
        LootDialog(generator, on_add=self.add_loot, parent=self).exec()

    def add_loot(self, roll: dict, confirm_replace: bool = True):
        """Add a rolled weapon, or equip a rolled armor set. Returns a status message."""
        data = self.character_data_for_save()
        if roll.get("kind") == "armor":
            current = data.get("armor")
            if current and confirm_replace:
                answer = QMessageBox.question(
                    self,
                    "Replace Worn Armor?",
                    f"Replace {current} with {character_loot.armor_name(roll)}?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return None
            name = character_loot.equip_armor(data, roll)
            message = f"{name} equipped."
        else:
            name = character_loot.add_weapon(data, roll)["name"]
            message = f"{name} added to Weapons."
        self.set_character(data, self.ruleset, self.game_data)
        return message + " Press Save on the character sheet to keep it."

    def set_save_available(self, available: bool):
        self.save_button.setEnabled(available)

    def character_data_for_save(self):
        other = {
            slot: box.value() for slot, box in self.dr_other_inputs.items() if box.value()
        }
        if other:
            self.character_data["damage_resistance_other"] = other
        else:
            self.character_data.pop("damage_resistance_other", None)
        self._store_energy_shield_inputs()
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

        columns = QHBoxLayout()
        columns.setSpacing(20)
        left_column = QVBoxLayout()
        left_column.setSpacing(18)
        self.characteristic_labels = self._add_characteristic_section(left_column)
        self.movement_labels = self._add_movement_section(left_column)
        self.carrying_capacity_labels = self._add_carrying_capacity_section(left_column)
        self._add_worn_armor_section(left_column)
        ability_section, self.ability_layout = self._new_section(
            "Abilities and Education"
        )
        left_column.addWidget(ability_section)
        outlier_section, self.outlier_layout = self._new_section("Outliers")
        left_column.addWidget(outlier_section)
        equipment_section, equipment_body = self._new_section("Equipment")
        self.equipment_pack_label = self._role_label("None", "strong")
        self.equipment_pack_label.setWordWrap(True)
        equipment_body.addWidget(self.equipment_pack_label)
        self.equipment_editor = QPlainTextEdit()
        self.equipment_editor.setPlaceholderText(
            "Add or remove equipment, one item per line..."
        )
        self.equipment_editor.setMinimumHeight(130)
        equipment_body.addWidget(self.equipment_editor)
        left_column.addWidget(equipment_section)
        left_column.addStretch(1)

        right_column = QVBoxLayout()
        right_column.setSpacing(18)
        self._add_resources_section(right_column)
        self._add_skill_section(right_column)
        right_column.addStretch(1)

        columns.addLayout(left_column, 3)
        columns.addLayout(right_column, 2)
        layout.addLayout(columns)

    def _build_combat_tab(self, layout):
        top_row = QHBoxLayout()
        top_row.setSpacing(28)
        vitals = QVBoxLayout()
        self._add_vitals_section(vitals)
        vitals.addStretch(1)
        gear = QVBoxLayout()
        gear.setSpacing(18)
        self.weapon_label = self._add_text_section(gear, "Weapons")
        self.armor_label = self._add_text_section(gear, "Armor")
        top_row.addLayout(vitals, 1)
        top_row.addLayout(gear, 3)
        layout.addLayout(top_row)

        layout.addWidget(self._build_damage_resistance_section())
        layout.addWidget(self._build_energy_shield_section())
        layout.addWidget(self._build_attack_calculator())

        throwing_section, throwing_body = self._new_section("Throwing Distance")
        throwing_body.addWidget(self._build_throwing_panel(), 0, 0)
        layout.addWidget(throwing_section)
        layout.addStretch(1)

    def _build_notes_tab(self, layout):
        notes_row = QHBoxLayout()
        notes_row.setSpacing(28)
        for key, title in (
            ("medical_notes", "Medical Information"),
            ("character_notes", "Character Information"),
            ("combat_notes", "Armor and Weapons Misc"),
        ):
            section, body = self._new_section(title)
            note = QPlainTextEdit()
            note.setPlaceholderText(f"Add {title.lower()}...")
            note.setMinimumHeight(420)
            body.addWidget(note, 0, 0)
            self.note_fields[key] = note
            notes_row.addWidget(section)
        layout.addLayout(notes_row)

    def _set_light_and_sky_powers(self, character, ruleset):
        """Show the Light & Sky tab (after Combat) for Light & Sky characters only."""
        index = self.tabs.indexOf(self.light_tab)
        if ruleset != "Light & Sky":
            if index != -1:
                self.tabs.removeTab(index)
            return
        if index == -1:
            self.tabs.insertTab(self.tabs.indexOf(self.combat_tab) + 1, self.light_tab, "Light && Sky")
        # The page edits character_data in place: energy and slotted powers save with it
        self.light_page.set_character(self.character_data, self.game_data, ruleset)

    def _create_scrollable_tab(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        content.setObjectName("sheetBody")
        content_layout = QVBoxLayout(content)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setContentsMargins(24, 18, 24, 24)
        content_layout.setSpacing(18)
        scroll.setWidget(content)
        return scroll, content_layout

    def _add_identity_section(self, parent_layout):
        section, grid = self._new_section("Service Record")
        grid.setHorizontalSpacing(28)
        fields = ("Soldier Type", "Rank", "Specialization", "Background", "Faction", "Race")
        labels = {}
        for index, field in enumerate(fields):
            row, column = divmod(index, 3)
            value_label = self._role_label("—", "form-line")
            value_label.setWordWrap(True)
            grid.addWidget(self._role_label(field.upper(), "caption"), row * 3, column)
            grid.addWidget(value_label, row * 3 + 1, column)
            grid.addWidget(self._new_rule("form-rule", 1), row * 3 + 2, column)
            grid.setColumnStretch(column, 1)
            labels[field] = value_label
        parent_layout.addWidget(section)
        return labels

    def _add_worn_armor_section(self, parent_layout):
        section, grid = self._new_section("Worn Armor")
        self.armor_equipped_checkbox = QCheckBox("Armor equipped")
        self.armor_equipped_checkbox.setToolTip(
            "When checked, the worn armor's characteristic bonuses and penalties "
            "are applied to characteristics, movement, carrying capacity, "
            "Perceptive Range, skill tests, and Max Wounds."
        )
        self.armor_equipped_checkbox.toggled.connect(self._on_armor_equipped_toggled)
        self.worn_armor_label = QLabel("No armor")
        self.worn_armor_label.setWordWrap(True)
        grid.addWidget(self.worn_armor_label, 0, 0)
        grid.addWidget(self.armor_equipped_checkbox, 1, 0)
        parent_layout.addWidget(section)

    def _on_armor_equipped_toggled(self, checked):
        self.character_data["armor_equipped"] = bool(checked)
        self._refresh_armor_effects()

    def _armor_context(self):
        """(armor records, soldier-type record) for the loaded character."""
        game_data = getattr(self, "game_data", None)
        if game_data is None:
            return {}, None
        return (
            armor_index(game_data),
            self._soldier_type_record(self.character_data, game_data),
        )

    def _effective_character(self):
        armors, soldier = self._armor_context()
        return worn_armor.effective_character(self.character_data, armors, soldier)

    def _refresh_armor_effects(self):
        """Re-derive every stat that worn armor changes."""
        character = getattr(self, "character_data", {}) or {}
        game_data = getattr(self, "game_data", None)
        armors, soldier = self._armor_context()
        bonus = worn_armor.armor_bonus(character, armors, soldier)
        equipped = worn_armor.is_equipped(character)
        effective = worn_armor.effective_character(character, armors, soldier)

        descriptions = getattr(self, "_characteristic_descriptions", {})
        characteristics = effective["characteristics"]
        for code, label in self.characteristic_labels.items():
            value = characteristics.get(code, "—")
            change = worn_armor.bonus_for(code, bonus) if equipped else 0
            label.setText(f"{value} ({change:+d})" if change else str(value))
            tooltip = descriptions.get(code, "")
            if change:
                tooltip = (tooltip + "\n\n" if tooltip else "") + (
                    f"Includes {change:+d} from worn armor "
                    f"({character.get('characteristics', {}).get(code)} base)."
                )
            label.setToolTip(tooltip)
        mythic = effective["mythic_characteristics"]
        for code, label in self.mythic_characteristic_labels.items():
            change = worn_armor.bonus_for(code, bonus, mythic=True) if equipped else 0
            if code in mythic:
                value = self._display_value(mythic[code])
                label.setText(f"{value} ({change:+d})" if change else value)
            else:
                label.setText("—")
            label.setToolTip(f"Includes {change:+d} Mythic from worn armor." if change else "")

        self._set_movement_speeds(effective, game_data)
        self._set_perceptive_range(effective, game_data)
        self._set_carrying_capacity(effective, game_data)
        self._set_max_wounds(character, effective)
        self._throwing_character = effective
        self._refresh_throwing()
        self._refresh_damage_resistance()
        self._refresh_energy_shield()
        self._refresh_attack()

        armor = character.get("armor")
        if not armor:
            self.worn_armor_label.setText("No armor")
        else:
            summary = format_bonus(bonus) or "no characteristic changes"
            state = "applied" if equipped else "not applied (armor removed)"
            self.worn_armor_label.setText(f"{armor}: {summary} - {state}")

    def _set_max_wounds(self, character, effective):
        """Max Wounds = 40 + TOU modifier x2 + Mythic TOU x2 (+ Robust, background)."""
        def wounds_for(stats):
            toughness = self._parse_integer((stats.get("characteristics") or {}).get("TOU"))
            if toughness is None:
                return None
            return max_wounds(
                toughness,
                (stats.get("mythic_characteristics") or {}).get("TOU", 0),
                self._as_list(stats.get("outliers")).count("Robust"),
                flat_bonus=self._parse_integer(stats.get("wounds_modifier")) or 0,
            )

        total = wounds_for(effective)
        if total is None:
            self.max_wounds_label.setText("Not available")
            return
        base = wounds_for(character)
        change = total - base if base is not None else 0
        self.max_wounds_label.setText(
            f"{total} ({change:+d} from worn armor)" if change else str(total)
        )

    def _add_characteristic_section(self, parent_layout):
        section, grid = self._new_section("Characteristics")
        grid.setSpacing(6)
        labels = {}
        self.characteristic_name_labels = {}
        mythic_labels = {}
        for index, (code, name) in enumerate(self.CHARACTERISTICS):
            tile = self._new_tile()
            body = QVBoxLayout(tile)
            body.setContentsMargins(3, 6, 3, 6)
            body.setSpacing(0)
            code_label = self._role_label(code, "tile-title", center=True)
            value = self._role_label("—", "stat", center=True)
            value.setWordWrap(True)
            name_label = self._role_label(name, "note", center=True)
            name_label.setWordWrap(True)
            body.addWidget(code_label)
            body.addWidget(value)
            body.addWidget(name_label)
            if code in {"STR", "TOU", "AGI"}:
                mythic_row = QHBoxLayout()
                mythic_row.setSpacing(4)
                mythic_value = self._role_label("—", "strong")
                mythic_row.addStretch(1)
                mythic_row.addWidget(self._role_label("MYTHIC", "caption"))
                mythic_row.addWidget(mythic_value)
                mythic_row.addStretch(1)
                body.addSpacing(4)
                body.addLayout(mythic_row)
                mythic_labels[code] = mythic_value
            body.addStretch(1)
            row, column = divmod(index, 5)
            grid.addWidget(tile, row, column)
            grid.setColumnStretch(column, 1)
            self.characteristic_name_labels[code] = code_label
            labels[code] = value
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
        self._characteristic_descriptions = descriptions
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
            self.ability_layout.addWidget(self._role_label("None", "note"))
            return

        for name in ability_names:
            label = DelayedTooltipLabel(
                name,
                descriptions.get(name.casefold(), ""),
            )
            label.setWordWrap(True)
            label.setStyleSheet(theme.SHEET_ABILITY)
            label.setIndent(0)
            self.ability_layout.addWidget(label)

    def _set_outlier_section(self, character, game_data):
        """One line per outlier taken, with its rank, picks and effect as the tooltip."""
        while self.outlier_layout.count():
            item = self.outlier_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        rows = outlier_rules.summary(game_data, character) if game_data else [
            {"name": name, "times": 1, "picks": [], "effect": ""}
            for name in dict.fromkeys(self._as_list(character.get("outliers")))
        ]
        if not rows:
            self.outlier_layout.addWidget(self._role_label("None", "note"), 0, 0)
            return
        for index, row in enumerate(rows):
            text = row["name"]
            if row["picks"]:
                text += ": " + ", ".join(row["picks"])
            elif row["times"] > 1:
                text += f" x{row['times']}"
            label = DelayedTooltipLabel(text, row["effect"])
            label.setWordWrap(True)
            label.setStyleSheet(theme.SHEET_ABILITY)
            label.setIndent(0)
            self.outlier_layout.addWidget(label, index, 0)

    def _refresh_outlier_readouts(self):
        """Fatigue penalty (Enduring ignores levels) and Natural Healing (Vigorous)."""
        character = getattr(self, "character_data", {}) or {}
        game_data = getattr(self, "game_data", None)
        rules = {}
        if game_data is not None:
            document = game_data.get("wounds", "wounds") or {}
            rules = document.get("wounds", {}) if isinstance(document, dict) else {}
        per_level = self._parse_integer((rules.get("fatigue") or {}).get("penalty_per_level"))
        per_level = -5 if per_level is None else per_level
        fatigue = self.resource_inputs["fatigue"].value()
        ignored = outlier_rules.ignored_fatigue_levels(game_data, character)
        penalty = per_level * max(0, fatigue - ignored)
        self.fatigue_penalty_label.setText(f"{penalty:+d}" if penalty else "None")
        self.fatigue_penalty_label.setToolTip(
            f"{per_level} per level of Fatigue"
            + (f"; Enduring ignores the first {ignored} levels." if ignored else ".")
        )
        base = self._parse_integer((rules.get("natural_healing") or {}).get("base_healing_per_day"))
        base = 1 if base is None else base
        multiplier = outlier_rules.natural_healing_multiplier(game_data, character)
        self.natural_healing_label.setText(f"{base * multiplier} Wound{'s' if base * multiplier != 1 else ''}/day")
        self.natural_healing_label.setToolTip(
            f"{base} per day" + (f", x{multiplier} from Vigorous." if multiplier > 1 else ".")
        )

    def _add_learned_labels(self, character):
        """Educations, Languages, Training and augmentations from the XP Shop."""
        groups = [
            (
                "Educations",
                [
                    f"{name} +{level}"
                    for name, level in (character.get("educations") or {}).items()
                ],
            ),
            ("Languages", self._as_list(character.get("languages"))),
            (
                "Weapon Training",
                self._as_list(character.get("weapon_training")),
            ),
            (
                "Faction Training",
                self._as_list(character.get("faction_training")),
            ),
            ("Augmentations", self._as_list(character.get("augmentations"))),
        ]
        wound_upgrades = self._integer_value(character.get("wound_upgrades"))
        if wound_upgrades:
            groups.append(("Wound Upgrades", [f"{wound_upgrades} (+{wound_upgrades * 10} Wounds)"]))
        for title, values in groups:
            if not values:
                continue
            label = QLabel(f"<b>{title}:</b> " + ", ".join(str(value) for value in values))
            label.setWordWrap(True)
            self.ability_layout.addWidget(label)

    def _add_movement_section(self, parent_layout):
        section, grid = self._new_section("Movement")
        labels = {}
        for column, (key, title) in enumerate(
            (
                ("half", "HALF"),
                ("full", "FULL"),
                ("charge", "CHARGE"),
                ("run", "RUN"),
                ("sprint", "SPRINT"),
                ("sight", "PERCEPTIVE RANGE"),
            )
        ):
            labels[key] = self._add_readout(grid, 0, column, title)
        labels["agility_modifier"] = self._role_label(
            "Agility Modifier: Not provided", "note"
        )
        grid.addWidget(labels["agility_modifier"], 2, 0, 1, 6)
        parent_layout.addWidget(section)
        return labels

    def _add_carrying_capacity_section(self, parent_layout):
        section, grid = self._new_section("Carrying Capacity (kg)")
        labels = {}
        for column, key in enumerate(("carry", "lift", "push")):
            labels[key] = self._add_readout(grid, 0, column, key.upper())
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
        self._carry_weight = values["carry"]

    def _display_unavailable_carrying_capacity(self, message: str):
        self._carry_weight = None
        for label in self.carrying_capacity_labels.values():
            label.setText(message)

    # ---------------------------------------------------------
    # Throwing distance
    # ---------------------------------------------------------
    def _build_throwing_panel(self):
        panel = QWidget()
        grid = QGridLayout(panel)
        grid.setContentsMargins(0, 0, 0, 8)

        self.throw_max_label = self._role_label("Not available", "stat-accent")
        self.throw_max_label.setToolTip(
            "Furthest a weightless object can go on a successful Warfare Melee "
            "Test: (Strength Modifier + Mythic Strength) x 15 Meters."
        )
        grid.addWidget(self.throw_max_label, 1, 0, 1, 5)
        self.throw_formula_label = QLabel("")
        self.throw_formula_label.setWordWrap(True)
        self.throw_formula_label.setProperty("role", "note")
        grid.addWidget(self.throw_formula_label, 2, 0, 1, 5)

        dof_label = QLabel("Degrees of Failure")
        self.throw_dof_input = QSpinBox()
        self.throw_dof_input.setRange(0, 30)
        self.throw_dof_input.setToolTip(
            "Each Degree of Failure on the Warfare Melee Test lowers the Multiplier by 1."
        )
        grip_label = QLabel("Grip")
        self.throw_grip_input = QComboBox()
        for name, (_, _, _, description) in throwing.GRIPS.items():
            self.throw_grip_input.addItem(name)
            self.throw_grip_input.setItemData(
                self.throw_grip_input.count() - 1, description, Qt.ItemDataRole.ToolTipRole
            )
        grid.addWidget(dof_label, 3, 0)
        grid.addWidget(self.throw_dof_input, 3, 1)
        grid.addWidget(grip_label, 3, 2)
        grid.addWidget(self.throw_grip_input, 3, 3)

        self.throw_table = QTableWidget(0, 3)
        self.throw_table.setHorizontalHeaderLabels(("Item", "Weight", "Range"))
        self.throw_table.verticalHeader().setVisible(False)
        self.throw_table.setShowGrid(False)
        self.throw_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.throw_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = self.throw_table.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        grid.addWidget(self.throw_table, 4, 0, 1, 5)

        custom_label = QLabel("Other object (kg)")
        self.throw_weight_input = QDoubleSpinBox()
        self.throw_weight_input.setRange(0, 10_000)
        self.throw_weight_input.setDecimals(2)
        self.throw_weight_input.setSingleStep(0.1)
        self.throw_custom_label = self._role_label("—", "strong")
        grid.addWidget(custom_label, 5, 0)
        grid.addWidget(self.throw_weight_input, 5, 1)
        grid.addWidget(self.throw_custom_label, 5, 2, 1, 3)
        grid.setColumnStretch(4, 1)
        grid.setHorizontalSpacing(10)

        self.throw_dof_input.valueChanged.connect(self._refresh_throwing)
        self.throw_grip_input.currentIndexChanged.connect(self._refresh_throwing)
        self.throw_weight_input.valueChanged.connect(self._refresh_throwing)
        return panel

    # ---------------------------------------------------------
    # Damage Resistance
    # ---------------------------------------------------------
    DR_PARTS = (
        ("armor", "ARMOR"),
        ("variant", "VAR"),
        ("toughness", "TOU"),
        ("mythic", "MYTHIC"),
    )

    def _build_damage_resistance_section(self):
        section, grid = self._new_section("Damage Resistance")
        grid.setSpacing(8)
        self.dr_labels: dict[str, dict[str, QLabel]] = {}
        self.dr_other_inputs: dict[str, QSpinBox] = {}
        for column, (slot, name, roll) in enumerate(damage_resistance.LOCATIONS):
            tile = self._new_tile()
            body = QVBoxLayout(tile)
            body.setContentsMargins(10, 8, 10, 10)
            body.setSpacing(4)
            heading = QHBoxLayout()
            heading.addWidget(self._role_label(name, "tile-title"))
            heading.addStretch(1)
            heading.addWidget(self._role_label(f"Hit roll {roll}", "note"))
            body.addLayout(heading)
            total = self._role_label("—", "stat-accent", center=True)
            body.addWidget(total)
            labels = {"total": total}
            parts = QGridLayout()
            parts.setHorizontalSpacing(4)
            parts.setVerticalSpacing(0)
            for part, (key, title) in enumerate(self.DR_PARTS):
                labels[key] = self._role_label("—", "strong", center=True)
                parts.addWidget(self._role_label(title, "caption", center=True), 0, part)
                parts.addWidget(labels[key], 1, part)
                parts.setColumnStretch(part, 1)
            body.addLayout(parts)
            other_row = QHBoxLayout()
            other_row.addWidget(self._role_label("OTHER", "caption"))
            box = QSpinBox()
            box.setRange(-100, 200)
            box.setToolTip(
                "Armor from Permutations, cover worn on the body, GM rulings... "
                "Saved with the character."
            )
            box.valueChanged.connect(self._refresh_damage_resistance)
            other_row.addWidget(box, 1)
            body.addLayout(other_row)
            grid.addWidget(tile, 0, column)
            grid.setColumnStretch(column, 1)
            self.dr_other_inputs[slot] = box
            self.dr_labels[slot] = labels
        self.dr_summary_label = self._role_label("", "note")
        self.dr_summary_label.setWordWrap(True)
        grid.addWidget(self.dr_summary_label, 1, 0, 1, len(damage_resistance.LOCATIONS))
        return section

    def _refresh_damage_resistance(self, *_):
        if not hasattr(self, "dr_labels"):
            return
        character = getattr(self, "character_data", {}) or {}
        stats = getattr(self, "_throwing_character", None) or {}
        toughness = self._parse_integer((stats.get("characteristics") or {}).get("TOU"))
        if toughness is None:
            for labels in self.dr_labels.values():
                for key in ("armor", "variant", "toughness", "mythic", "total"):
                    labels[key].setText("—")
            self.dr_summary_label.setText("Load a character to see Damage Resistance.")
            return

        game_data = getattr(self, "game_data", None)
        armors = armor_index(game_data) if game_data else {}
        armor = damage_resistance.armor_ratings(character, armors, game_data)
        mythic = (stats.get("mythic_characteristics") or {}).get("TOU", 0)
        table = damage_resistance.damage_resistance(
            toughness, mythic, armor, {slot: box.value() for slot, box in self.dr_other_inputs.items()}
        )
        for slot, parts in table.items():
            labels = self.dr_labels[slot]
            labels["armor"].setText(str(parts["armor"]))
            labels["variant"].setText(f"{parts['variant']:+d}" if parts["variant"] else "—")
            labels["toughness"].setText(str(parts["toughness"]))
            labels["mythic"].setText(str(parts["mythic"]))
            labels["total"].setText(str(parts["total"]))
            labels["total"].setToolTip(
                " + ".join(
                    f"{parts[key]} {title}"
                    for key, title in (
                        ("armor", "Armor"), ("variant", "Variant"), ("toughness", "Toughness Modifier"),
                        ("mythic", "Mythic Toughness"), ("other", "Other"),
                    )
                    if parts[key] or key in ("armor", "toughness")
                )
            )

        lines = [f"Damage Resistance = Toughness Modifier ({table['head']['toughness']}) "
                 f"+ Mythic Toughness ({table['head']['mythic']}) + Armor Rating for the location hit."]
        if not armor["name"]:
            lines.append("No armor worn.")
        elif not armor["equipped"]:
            lines.append(f"{armor['name']} is removed, so it adds no Armor.")
        elif not armor["found"]:
            lines.append(f"Armor Ratings for {armor['name']} aren't in the data; use Other.")
        else:
            worn = armor["name"] + (f" ({armor['variant']} variant)" if armor["variant"] else "")
            lines.append(f"Wearing {worn}.")
        if armor["equipped"]:
            for note in armor.get("variant_notes", []):
                lines.append(f"Not included (situational): {note}")
        self.dr_summary_label.setText("\n".join(lines))

    # ---------------------------------------------------------
    # Energy Shields
    # ---------------------------------------------------------
    def _shield_tile(self, grid, column, title):
        tile = self._new_tile()
        body = QVBoxLayout(tile)
        body.setContentsMargins(8, 6, 8, 8)
        body.setSpacing(0)
        value = self._role_label("—", "stat-accent", center=True)
        body.addWidget(self._role_label(title.upper(), "caption", center=True))
        body.addWidget(value)
        grid.addWidget(tile, 0, column, 2, 1)
        return value

    def _build_energy_shield_section(self):
        section, grid = self._new_section("Energy Shields")
        self.shield_labels = {
            "integrity": self._shield_tile(grid, 0, "Shield Integrity"),
            "delay": self._shield_tile(grid, 1, "Delay in Rounds"),
            "recharge": self._shield_tile(grid, 2, "Recharge per Round"),
        }
        self.shield_labels["delay"].setToolTip(
            "Rounds before the shield starts recharging. Taking 10+ Damage in a Round resets it."
        )

        tracker = QGridLayout()
        tracker.setHorizontalSpacing(10)
        tracker.addWidget(self._form_label("Current"), 0, 0)
        self.shield_current_input = QSpinBox()
        self.shield_current_input.setRange(0, 0)
        self.shield_current_input.setToolTip("Shield Integrity left. Saved with the character.")
        tracker.addWidget(self.shield_current_input, 0, 1)
        self.shield_recharge_button = QPushButton("Recharge")
        self.shield_recharge_button.setToolTip("Add one Round of Recharge Rate (after the Delay has passed).")
        self.shield_recharge_button.clicked.connect(self._recharge_energy_shield)
        self.shield_full_button = QPushButton("Full")
        self.shield_full_button.clicked.connect(
            lambda: self.shield_current_input.setValue(self.shield_current_input.maximum())
        )
        tracker.addWidget(self.shield_recharge_button, 0, 2)
        tracker.addWidget(self.shield_full_button, 0, 3)
        tracker.addWidget(self._form_label("Other Integrity"), 1, 0)
        self.shield_other_input = QSpinBox()
        self.shield_other_input.setRange(-500, 1000)
        self.shield_other_input.setSingleStep(5)
        self.shield_other_input.setToolTip(
            "Extra Shield Integrity from Permutations (e.g. UA/SIMA-Alpha +50) or GM rulings. "
            "Saved with the character."
        )
        self.shield_other_input.valueChanged.connect(self._refresh_energy_shield)
        tracker.addWidget(self.shield_other_input, 1, 1)
        self.shield_panels_input = QCheckBox("Photo-Reactive Panels active")
        self.shield_panels_input.setToolTip("SPI armor: Recharge Rate halved and Delay doubled while active.")
        self.shield_panels_input.toggled.connect(self._refresh_energy_shield)
        tracker.addWidget(self.shield_panels_input, 1, 2, 1, 2)
        grid.addLayout(tracker, 0, 3, 2, 1)

        self.shield_source_label = self._form_label("")
        self.shield_source_label.setWordWrap(True)
        self.shield_source_label.setProperty("role", "strong")
        grid.addWidget(self.shield_source_label, 2, 0, 1, 4)
        self.shield_notes_label = self._form_label("")
        self.shield_notes_label.setWordWrap(True)
        self.shield_notes_label.setProperty("role", "note")
        grid.addWidget(self.shield_notes_label, 3, 0, 1, 4)
        for column in range(4):
            grid.setColumnStretch(column, 1)
        return section

    def _load_energy_shield_inputs(self, character):
        self.shield_other_input.blockSignals(True)
        self.shield_other_input.setValue(self._integer_value(character.get("energy_shield_other")))
        self.shield_other_input.blockSignals(False)
        self.shield_panels_input.blockSignals(True)
        self.shield_panels_input.setChecked(bool(character.get("energy_shield_panels_active")))
        self.shield_panels_input.blockSignals(False)
        current = self._parse_integer(character.get("energy_shield_current"))
        self._shield_pending_current = current  # None: start full

    def _store_energy_shield_inputs(self):
        data = self.character_data
        for key, value in (
            ("energy_shield_other", self.shield_other_input.value()),
            ("energy_shield_panels_active", self.shield_panels_input.isChecked()),
        ):
            if value:
                data[key] = value
            else:
                data.pop(key, None)
        if self.shield_current_input.isEnabled():
            data["energy_shield_current"] = self.shield_current_input.value()
        else:
            data.pop("energy_shield_current", None)

    def _current_energy_shield(self):
        game_data = getattr(self, "game_data", None)
        armors = armor_index(game_data) if game_data else {}
        return energy_shields.energy_shield(
            getattr(self, "character_data", {}) or {},
            armors,
            getattr(self, "ruleset", ""),
            game_data,
            panels_active=self.shield_panels_input.isChecked(),
            other_integrity=self.shield_other_input.value(),
        )

    def _recharge_energy_shield(self):
        shield = self._current_energy_shield()
        self.shield_current_input.setValue(
            energy_shields.recharge(self.shield_current_input.value(), shield)
        )

    def _refresh_energy_shield(self, *_):
        if not hasattr(self, "shield_labels"):
            return
        shield = self._current_energy_shield()
        has = shield["has_shield"]
        for key, label in self.shield_labels.items():
            label.setText(str(shield[key]) if has else "—")
        current_box = self.shield_current_input
        previous_max = current_box.maximum()
        pending = getattr(self, "_shield_pending_current", "unset")
        current_box.blockSignals(True)
        current_box.setMaximum(shield["integrity"] if has else 0)
        if has and pending != "unset":
            current_box.setValue(shield["integrity"] if pending is None else pending)
            self._shield_pending_current = "unset"
        elif has and current_box.value() == previous_max:
            current_box.setValue(shield["integrity"])  # stay full when the maximum changes
        current_box.blockSignals(False)
        for widget in (current_box, self.shield_recharge_button, self.shield_full_button):
            widget.setEnabled(has)
        self.shield_recharge_button.setText(f"Recharge (+{shield['recharge']})" if has else "Recharge")
        self.shield_panels_input.setVisible(shield["spi"])

        if has:
            source = f"From {shield['source']}"
            if shield["variant"] and shield["variant_modifiers"]:
                changes = ", ".join(
                    f"{value:+d} {key.title()}" for key, value in shield["variant_modifiers"].items()
                )
                source += f" ({shield['variant']} variant: {changes})"
            self.shield_source_label.setText(source + ".")
            notes = list(shield["notes"]) + list(energy_shields.RULE_NOTES)
        else:
            self.shield_source_label.setText("No Energy Shield.")
            notes = list(shield["notes"])
        self.shield_notes_label.setText("\n".join(f"• {note}" for note in notes))

    # ---------------------------------------------------------
    # Attack calculator
    # ---------------------------------------------------------
    @staticmethod
    def _form_label(text):
        return QLabel(text)

    @staticmethod
    def _fill_combo(combo, items, keep=None):
        """Replace a combo's (key, label) items, keeping the current key when possible."""
        current = keep if keep is not None else combo.currentData()
        combo.blockSignals(True)
        combo.clear()
        for key, label in items:
            combo.addItem(label, key)
        index = combo.findData(current)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

    def _build_attack_calculator(self):
        section, grid = self._new_section("Attack Calculator")
        self._attack_ability_boxes: dict[str, QCheckBox] = {}
        self._attack_ability_notes: list[QLabel] = []
        self._attack_ability_state: dict[str, bool] = {}
        self._attack_profiles: list = []

        # Column 1: the attack
        attack_box = QGridLayout()
        attack_box.setHorizontalSpacing(12)
        row = 0

        def add_row(text, widget):
            nonlocal row
            attack_box.addWidget(self._form_label(text), row, 0)
            attack_box.addWidget(widget, row, 1)
            row += 1

        self.attack_weapon_input = QComboBox()
        add_row("Weapon", self.attack_weapon_input)
        self.attack_mode_input = QComboBox()
        add_row("Attack", self.attack_mode_input)
        self.attack_fire_mode_input = QComboBox()
        self.attack_fire_mode_input.setToolTip("Semi-Auto and Burst fire give +10 To Hit.")
        add_row("Fire rate", self.attack_fire_mode_input)
        self.attack_range_input = QComboBox()
        add_row("Range", self.attack_range_input)
        self.attack_wielding_input = QComboBox()
        for key, label in (("two", "Normal grip"), ("one", "One-handed"), ("dual", "Dual wielding")):
            self.attack_wielding_input.addItem(label, key)
        add_row("Wielding", self.attack_wielding_input)
        self.attack_braced_input = QCheckBox("Braced")
        self.attack_braced_input.setToolTip(
            "[HW] weapons take -20 unless Braced (Half Action). Bracing also halves "
            "One-handed and Dual Wielding Penalties."
        )
        add_row("", self.attack_braced_input)
        self.attack_aim_input = QComboBox()
        for key, (label, value) in attack.AIM.items():
            self.attack_aim_input.addItem(f"{label} ({value:+d})" if value else label, key)
        add_row("Aim", self.attack_aim_input)
        self.attack_laser_input = QCheckBox("Targeting laser (+5)")
        self.attack_laser_input.setToolTip(
            "+5 To Hit if the target is within half your Perceptive Range. Doesn't stack with Aim."
        )
        add_row("", self.attack_laser_input)
        self.attack_movement_input = QComboBox()
        for key, (label, ranged, melee) in attack.MOVEMENT.items():
            self.attack_movement_input.addItem(label, key)
        self.attack_movement_input.setToolTip(
            "Attacking while moving: Half or Full Move -20, Charge -30 (a melee Charge Attack "
            "gets +10 instead), Run -40."
        )
        add_row("Moving", self.attack_movement_input)
        self.attack_first_charge_shot_input = QCheckBox("First shot of the Charge")
        self.attack_first_charge_shot_input.setChecked(True)
        self.attack_first_charge_shot_input.setToolTip("Aggressive Advance: the first shot of a Charge has no Penalty.")
        add_row("", self.attack_first_charge_shot_input)
        self.attack_called_shot_input = QCheckBox("Called Shot")
        self.attack_called_target_input = QComboBox()
        for key, (label, value) in attack.CALLED_SHOTS.items():
            self.attack_called_target_input.addItem(f"{label} ({value})", key)
        attack_box.addWidget(self.attack_called_shot_input, row, 0)
        attack_box.addWidget(self.attack_called_target_input, row, 1)
        row += 1
        attack_box.setColumnStretch(1, 1)
        attack_box.setRowStretch(row, 1)

        # Column 2: conditions and other modifiers
        conditions_box = QGridLayout()
        conditions_box.setHorizontalSpacing(12)
        self.attack_condition_inputs: dict[str, QComboBox] = {}
        condition_tables = (
            ("lighting", "Lighting", attack.LIGHTING),
            ("weather", "Weather", attack.WEATHER),
            ("perceptive", "Distance", attack.PERCEPTIVE),
            ("target_stance", "Target is", attack.TARGET_STANCE),
            ("target_size", "Target size", attack.TARGET_SIZE),
            ("speed", "Speed", attack.SPEED),
            ("blind_fire", "Visibility", attack.BLIND_FIRE),
        )
        for index, (key, title, table) in enumerate(condition_tables):
            combo = QComboBox()
            for option, values in table.items():
                label = values[0]
                numbers = [value for value in values[1:] if value]
                if key == "target_stance" and numbers:
                    label += f" ({values[1]:+d} ranged, {values[2]:+d} melee)"
                elif numbers:
                    label += f" ({numbers[0]:+d})"
                combo.addItem(label, option)
            conditions_box.addWidget(self._form_label(title), index, 0)
            conditions_box.addWidget(combo, index, 1)
            self.attack_condition_inputs[key] = combo
        row = len(condition_tables)
        self.attack_situational_inputs: dict[str, QCheckBox] = {}
        for key, (label, value, _) in attack.SITUATIONAL.items():
            box = QCheckBox(f"{label} ({value:+d})")
            conditions_box.addWidget(box, row, 0, 1, 2)
            self.attack_situational_inputs[key] = box
            row += 1
        self.attack_custom_input = QSpinBox()
        self.attack_custom_input.setRange(-300, 300)
        self.attack_custom_input.setSingleStep(5)
        self.attack_custom_input.setToolTip("Any other Bonus or Penalty: scopes, grips, GM rulings...")
        conditions_box.addWidget(self._form_label("Other / GM"), row, 0)
        conditions_box.addWidget(self.attack_custom_input, row, 1)
        conditions_box.setColumnStretch(1, 1)
        conditions_box.setRowStretch(row + 1, 1)

        # Column 3: abilities and the result
        result_box = QVBoxLayout()
        abilities_title = self._role_label("ABILITIES", "caption")
        result_box.addWidget(abilities_title)
        self.attack_ability_layout = QVBoxLayout()
        result_box.addLayout(self.attack_ability_layout)
        self.attack_no_abilities_label = self._form_label("No abilities affect this attack.")
        self.attack_no_abilities_label.setProperty("role", "note")
        result_box.addWidget(self.attack_no_abilities_label)

        self.attack_total_label = self._role_label("Roll under —", "roll-target", center=True)
        result_box.addSpacing(8)
        result_box.addWidget(self.attack_total_label)
        self.attack_roll_button = QPushButton("Roll Attack")
        self.attack_roll_button.setToolTip("Roll the To Hit Test against this total.")
        self.attack_roll_button.setEnabled(False)
        self.attack_roll_button.clicked.connect(self.open_attack_roll)
        result_box.addWidget(self.attack_roll_button)
        self.attack_base_label = self._form_label("")
        self.attack_base_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        result_box.addWidget(self.attack_base_label)
        self.attack_breakdown_label = self._form_label("")
        self.attack_breakdown_label.setWordWrap(True)
        self.attack_breakdown_label.setTextFormat(Qt.TextFormat.RichText)
        result_box.addWidget(self.attack_breakdown_label)
        self.attack_notes_label = self._form_label("")
        self.attack_notes_label.setWordWrap(True)
        self.attack_notes_label.setProperty("role", "note")
        result_box.addWidget(self.attack_notes_label)
        result_box.addStretch(1)

        grid.addLayout(attack_box, 0, 0)
        grid.addLayout(conditions_box, 0, 1)
        grid.addLayout(result_box, 0, 2)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        grid.setHorizontalSpacing(24)

        # Wiring
        self.attack_weapon_input.currentIndexChanged.connect(self._on_attack_weapon_changed)
        self.attack_mode_input.currentIndexChanged.connect(self._on_attack_mode_changed)
        for combo in (
            self.attack_fire_mode_input, self.attack_range_input, self.attack_wielding_input,
            self.attack_aim_input, self.attack_movement_input, self.attack_called_target_input,
            *self.attack_condition_inputs.values(),
        ):
            combo.currentIndexChanged.connect(self._refresh_attack)
        for combo in section.findChildren(QComboBox):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(12)
        for box in (
            self.attack_braced_input, self.attack_laser_input, self.attack_first_charge_shot_input,
            self.attack_called_shot_input, *self.attack_situational_inputs.values(),
        ):
            box.toggled.connect(self._refresh_attack)
        self.attack_custom_input.valueChanged.connect(self._refresh_attack)
        return section

    def attack_roll_dialog(self):
        """The roll window for the current attack (not shown), or None."""
        self._refresh_attack()
        result = getattr(self, "_attack_result", None)
        if result is None:
            return None
        title = f"{self._attack_profile().name} - {self.attack_mode_input.currentText()}"
        return AttackRollDialog(title, result, rng=self.dice_rng, parent=self)

    def open_attack_roll(self):
        dialog = self.attack_roll_dialog()
        if dialog is not None:
            dialog.exec()

    def _populate_attack_weapons(self):
        game_data = getattr(self, "game_data", None)
        armory = armory_index(game_data) if game_data else {}
        self._attack_profiles = [attack.weapon_profile(attack.UNARMED)] + [
            attack.weapon_profile(weapon, armory)
            for weapon in self._as_list(self.character_data.get("weapons"))
            if weapon
        ]
        previous = self.attack_weapon_input.currentText()
        combo = self.attack_weapon_input
        combo.blockSignals(True)
        combo.clear()
        for index, profile in enumerate(self._attack_profiles):
            combo.addItem(profile.name, index)
        found = combo.findText(previous)
        default = 1 if len(self._attack_profiles) > 1 else 0
        combo.setCurrentIndex(found if found >= 0 else default)
        combo.blockSignals(False)
        self._on_attack_weapon_changed()

    def _attack_profile(self):
        index = self.attack_weapon_input.currentData()
        profiles = getattr(self, "_attack_profiles", [])
        if isinstance(index, int) and 0 <= index < len(profiles):
            return profiles[index]
        return attack.weapon_profile(attack.UNARMED)

    def _on_attack_weapon_changed(self, *_):
        profile = self._attack_profile()
        self._fill_combo(
            self.attack_mode_input,
            [(mode, attack.MODE_LABELS[mode]) for mode in profile.modes],
            keep=profile.default_mode,
        )
        self._fill_combo(
            self.attack_fire_mode_input,
            [(mode.label, mode.label + (f" (+{mode.bonus})" if mode.bonus else "")) for mode in profile.fire_modes],
        )
        untrained = self._attack_untrained(profile)
        box = self.attack_situational_inputs["untrained"]
        box.blockSignals(True)
        box.setChecked(bool(untrained))
        box.blockSignals(False)
        box.setToolTip(
            "Couldn't tell which Weapon Training covers this weapon; tick it if you lack it."
            if untrained is None
            else "Set from the character's Weapon Training. Untick if the GM rules otherwise."
        )
        self.attack_braced_input.setEnabled(profile.wield_tag == "HW")
        if profile.wield_tag != "HW":
            self.attack_braced_input.setChecked(False)
        self._on_attack_mode_changed()

    def _attack_untrained(self, profile):
        game_data = getattr(self, "game_data", None)
        if game_data is None:
            return None
        try:
            owned = XpShop(self.character_data, game_data, self.ruleset).owned_weapon_training()
        except Exception:  # an incomplete character shouldn't break the sheet
            return None
        return attack.is_untrained(profile, owned, game_data.get("weapon_training", "weapon_training"))

    def _on_attack_mode_changed(self, *_):
        profile = self._attack_profile()
        mode = self.attack_mode_input.currentData() or profile.default_mode
        bands = attack.range_bands(profile, mode)
        current = self.attack_range_input.currentData()
        keys = [key for key, _, _ in bands]
        self._fill_combo(
            self.attack_range_input,
            [(key, f"{label} ({value:+d})" if value else label) for key, label, value in bands],
            keep=current if current in keys else attack.default_range(profile, mode),
        )
        firing = mode == attack.FIRE
        self.attack_fire_mode_input.setEnabled(firing and self.attack_fire_mode_input.count() > 0)
        self.attack_laser_input.setEnabled(firing)
        self.attack_wielding_input.setEnabled(mode != attack.THROW and profile.wield_tag is not None)
        self.attack_condition_inputs["blind_fire"].setEnabled(firing)
        self.attack_condition_inputs["perceptive"].setEnabled(mode != attack.MELEE)
        for key, box in self.attack_situational_inputs.items():
            box.setEnabled(mode in attack.SITUATIONAL[key][2])
        self._rebuild_attack_abilities(profile, mode)
        self._refresh_attack()

    def _rebuild_attack_abilities(self, profile, mode):
        for name, box in self._attack_ability_boxes.items():
            self._attack_ability_state[name] = box.isChecked()
            self.attack_ability_layout.removeWidget(box)
            box.deleteLater()
        for note in self._attack_ability_notes:
            self.attack_ability_layout.removeWidget(note)
            note.deleteLater()
        self._attack_ability_boxes = {}
        self._attack_ability_notes = []
        relevant = attack.relevant_abilities(self.character_data.get("abilities"), profile, mode)
        for name, effect, default in relevant:
            box = QCheckBox(name)
            box.setChecked(self._attack_ability_state.get(name, default))
            box.toggled.connect(self._refresh_attack)
            note = self._role_label(effect, "note")
            note.setWordWrap(True)
            self.attack_ability_layout.addWidget(box)
            self.attack_ability_layout.addWidget(note)
            self._attack_ability_boxes[name] = box
            self._attack_ability_notes.append(note)
        self.attack_no_abilities_label.setVisible(not relevant)

    def _attack_options(self, profile, mode, characteristic, mythic_strength):
        fire_label = self.attack_fire_mode_input.currentData()
        fire_mode = next((m for m in profile.fire_modes if m.label == fire_label), None)
        return attack.AttackOptions(
            characteristic=characteristic,
            mythic_strength=mythic_strength,
            mode=mode,
            fire_mode=fire_mode,
            range_band=self.attack_range_input.currentData() or "optimal",
            wielding=self.attack_wielding_input.currentData() or "two",
            braced=self.attack_braced_input.isChecked(),
            aim=self.attack_aim_input.currentData() or "none",
            laser=self.attack_laser_input.isChecked(),
            movement=self.attack_movement_input.currentData() or "none",
            first_charge_shot=self.attack_first_charge_shot_input.isChecked(),
            called_shot=self.attack_called_shot_input.isChecked(),
            called_target=self.attack_called_target_input.currentData() or "location",
            situational={key for key, box in self.attack_situational_inputs.items() if box.isChecked()},
            abilities={name for name, box in self._attack_ability_boxes.items() if box.isChecked()},
            custom=self.attack_custom_input.value(),
            **{key: combo.currentData() for key, combo in self.attack_condition_inputs.items()},
        )

    def _refresh_attack(self, *_):
        if not hasattr(self, "attack_total_label"):
            return
        profile = self._attack_profile()
        mode = self.attack_mode_input.currentData() or profile.default_mode
        self.attack_called_target_input.setEnabled(self.attack_called_shot_input.isChecked())
        self.attack_first_charge_shot_input.setVisible(
            "Aggressive Advance" in self._attack_ability_boxes
            and self.attack_movement_input.currentData() == "charge"
        )
        stats = getattr(self, "_throwing_character", None) or {}
        code = attack.MODE_CHARACTERISTIC.get(mode, "WFR")
        value = self._parse_integer((stats.get("characteristics") or {}).get(code))
        self.attack_roll_button.setEnabled(value is not None)
        self._attack_result = None
        if value is None:
            self.attack_total_label.setText("Roll under —")
            self.attack_base_label.setText("Load a character to calculate attacks.")
            self.attack_breakdown_label.setText("")
            self.attack_notes_label.setText("")
            return
        mythic_strength = throwing.mythic_value((stats.get("mythic_characteristics") or {}).get("STR", 0))
        result = attack.attack_target(
            profile, self._attack_options(profile, mode, value, mythic_strength)
        )
        self._attack_result = result
        names = {"WFR": "Warfare Range", "WFM": "Warfare Melee"}
        self.attack_total_label.setText(f"Roll {result.total} or under")
        self.attack_total_label.setToolTip("Roll 1D100. A natural 01 is a critical success.")
        modifier = result.total_modifier
        self.attack_base_label.setText(
            f"{names[result.characteristic_name]} ({result.characteristic_name}) {result.characteristic}"
            + (f" {modifier:+d}" if modifier else ", no modifiers")
        )
        rows = "".join(
            f"<tr><td style='padding-right:12px; color:{theme.SHEET_GOOD if amount > 0 else theme.SHEET_BAD};'>"
            f"<b>{amount:+d}</b></td><td>{html.escape(label)}</td></tr>"
            for label, amount in result.modifiers
        )
        self.attack_breakdown_label.setText(f"<table>{rows}</table>" if rows else "")
        self.attack_notes_label.setText("\n".join(result.notes))

    def _throwing_items(self):
        """(name, weight kg) for each carried weapon with a known weight, lightest first."""
        game_data = getattr(self, "game_data", None)
        armory = armory_index(game_data) if game_data else {}
        items = []
        for weapon in self._as_list(self.character_data.get("weapons")):
            name = weapon.get("name") if isinstance(weapon, dict) else weapon
            if not isinstance(name, str):
                continue
            weight = weapon.get("weight_kg") if isinstance(weapon, dict) else None
            if weight is None:
                weight = (armory.get(name) or {}).get("weight_kg")
            try:
                weight = float(weight)
            except (TypeError, ValueError):
                continue
            label = weapon.get("nickname") if isinstance(weapon, dict) else None
            items.append((f"{name} ({label})" if label else name, weight))
        return sorted(items, key=lambda item: item[1])

    def _refresh_throwing(self, *_):
        character = getattr(self, "_throwing_character", None) or {}
        strength = self._parse_integer((character.get("characteristics") or {}).get("STR"))
        self.throw_table.setRowCount(0)
        if strength is None:
            self.throw_max_label.setText("Not available")
            self.throw_formula_label.setText("")
            self.throw_custom_label.setText("—")
            return

        mythic = (character.get("mythic_characteristics") or {}).get("STR", 0)
        modifier = strength // 10
        total = throwing.throw_strength(strength, mythic)
        carry = getattr(self, "_carry_weight", None)
        grip = self.throw_grip_input.currentText()
        dof = self.throw_dof_input.value()

        def result(weight=0.0, **overrides):
            options = {"grip": grip, "degrees_of_failure": dof, "carry_weight": carry}
            options.update(overrides)
            return throwing.throw_distance(strength, mythic, weight, **options)

        best = result(grip="Solid", degrees_of_failure=0)
        self.throw_max_label.setText(f"Max {best.range_text()}")
        step_kg, per_step = throwing.weight_step(total)
        lines = [
            f"(STR Mod {modifier} + Mythic STR {throwing.mythic_value(mythic)}) x 15. "
            f"-{total} m per Degree of Failure.",
            f"Weight: every {step_kg:g} kg lowers the x15 by {per_step}.",
        ]
        if carry is not None:
            lines.append(f"Can't throw anything over Carry Weight ({carry:g} kg).")
        self.throw_formula_label.setText("\n".join(lines))

        items = self._throwing_items()
        self.throw_table.setVisible(bool(items))
        for row, (name, weight) in enumerate(items):
            throw = result(weight)
            self.throw_table.insertRow(row)
            cells = (name, f"{weight:g} kg", throw.range_text())
            for column, text in enumerate(cells):
                cell = QTableWidgetItem(text)
                cell.setToolTip(throw.explanation)
                if column == 2:
                    cell.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.throw_table.setItem(row, column, cell)
        if items:
            height = self.throw_table.horizontalHeader().height() + 4
            height += sum(self.throw_table.rowHeight(r) for r in range(len(items)))
            self.throw_table.setFixedHeight(min(height, 220))

        custom = result(self.throw_weight_input.value())
        text = custom.range_text()
        if custom.can_throw and custom.to_hit:
            text += f" ({custom.to_hit} To Hit)"
        self.throw_custom_label.setText(text)
        self.throw_custom_label.setToolTip(custom.explanation)

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
        multipliers = movement_rules.get("multipliers")
        if movement is None and agility_modifier > 0 and isinstance(multipliers, dict):
            # The table stops at 9, but the book says movement continues past
            # it using the same multipliers (Half 1x ... Sprint 8x).
            movement = {
                key: agility_modifier * value
                for key, value in multipliers.items()
                if isinstance(value, (int, float))
            }
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
        # Aspects only work while slotted; older saves without a loadout use every owned one
        loadout = character.get("light_loadout")
        if isinstance(loadout, dict) and isinstance(loadout.get("aspects"), list):
            raw_selected_aspects = [name for name in loadout["aspects"] if name]
        else:
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

    SKILL_PIP_WIDTH = 46

    def _add_skill_section(self, parent_layout):
        section, body = self._new_section("Skills")
        header = QHBoxLayout()
        header.setContentsMargins(4, 0, 0, 0)
        header.setSpacing(0)
        header.addWidget(self._role_label("Click a skill to roll a test", "note"), 1)
        for title in ("TRAINED", "+10", "+20"):
            caption = self._role_label(title, "caption", center=True)
            caption.setFixedWidth(self.SKILL_PIP_WIDTH)
            header.addWidget(caption)
        self.skill_list = QVBoxLayout()
        self.skill_list.setSpacing(0)
        self.skill_rows: dict[str, QPushButton] = {}
        body.addLayout(header, 0, 0)
        body.addLayout(self.skill_list, 1, 0)
        parent_layout.addWidget(section)

    def _new_skill_row(self, name, trained, value):
        row = QPushButton()
        row.setProperty("role", "skill")
        row.setFixedHeight(25)
        row.setCursor(Qt.CursorShape.PointingHandCursor)
        row.setToolTip(f"Roll a {name} test")
        row.setAccessibleName(name)
        row.clicked.connect(lambda _=False, skill=name: self._open_skill_test(skill))
        layout = QHBoxLayout(row)
        layout.setContentsMargins(4, 0, 0, 0)
        layout.setSpacing(0)
        cells = [self._role_label(name, "skill-trained" if trained else "skill-untrained")]
        layout.addWidget(cells[0], 1)
        for selected in (trained, trained and value >= 10, trained and value >= 20):
            pip = QFrame()
            pip.setProperty("role", "pip-on" if selected else "pip-off")
            pip.setFixedSize(12, 12)
            slot = QWidget()
            slot.setFixedWidth(self.SKILL_PIP_WIDTH)
            slot_layout = QHBoxLayout(slot)
            slot_layout.setContentsMargins(0, 0, 0, 0)
            slot_layout.addWidget(pip, 0, Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(slot)
            cells += [slot, pip]
        for cell in cells:
            cell.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        return row

    def _set_skill_rows(self, skills, game_data):
        for row in self.skill_rows.values():
            self.skill_list.removeWidget(row)
            row.setParent(None)
            row.deleteLater()
        self.skill_rows = {}
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
            row = self._new_skill_row(name, trained, value)
            self.skill_list.addWidget(row)
            self.skill_rows[name] = row

    def _open_skill_test(self, skill_name):
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
        characteristic_values = self._effective_character().get("characteristics")
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
            rng=self.dice_rng,
        )
        dialog.exec()

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

    def _resource_spin_box(self, key):
        spin_box = QSpinBox()
        spin_box.setRange(0, 1_000_000)
        spin_box.valueChanged.connect(
            lambda value, field=key: self.character_data.__setitem__(field, value)
        )
        return spin_box

    def _add_resources_section(self, parent_layout):
        section, grid = self._new_section("Resources")
        self.resource_inputs = {"credits": self._resource_spin_box("credits")}
        available = QSpinBox()
        available.setRange(0, 0)
        total = QSpinBox()
        total.setRange(0, 1_000_000)
        available.valueChanged.connect(
            lambda value: self.character_data.__setitem__("luck_available", value)
        )
        total.valueChanged.connect(self._set_luck_total)
        self.luck_inputs = {"available": available, "total": total}
        for column, (title, widget) in enumerate(
            (
                ("LUCK AVAILABLE", available),
                ("LUCK TOTAL", total),
                ("CREDITS", self.resource_inputs["credits"]),
            )
        ):
            grid.addWidget(self._role_label(title, "caption"), 0, column)
            grid.addWidget(widget, 1, column)
            grid.setColumnStretch(column, 1)
        self.resource_inputs["support_points"] = self._resource_spin_box("support_points")
        grid.addWidget(self._role_label("SUPPORT POINTS", "caption"), 2, 0)
        grid.addWidget(self.resource_inputs["support_points"], 3, 0)
        parent_layout.addWidget(section)

    def _add_vitals_section(self, parent_layout):
        section, grid = self._new_section("Vitals")
        self.resource_inputs["wounds"] = self._resource_spin_box("wounds")
        self.resource_inputs["wounds"].setProperty("role", "vital")
        self.resource_inputs["fatigue"] = self._resource_spin_box("fatigue")
        self.resource_inputs["fatigue"].setProperty("role", "vital")
        grid.addWidget(self._role_label("WOUNDS", "caption"), 0, 0)
        grid.addWidget(self.resource_inputs["wounds"], 1, 0)
        grid.addWidget(self._role_label("MAX WOUNDS", "caption"), 2, 0)
        self.max_wounds_label = self._role_label("—", "readout")
        self.max_wounds_label.setWordWrap(True)
        grid.addWidget(self.max_wounds_label, 3, 0)
        grid.addWidget(self._role_label("FATIGUE", "caption"), 4, 0)
        grid.addWidget(self.resource_inputs["fatigue"], 5, 0)
        self.resource_inputs["fatigue"].valueChanged.connect(
            lambda _value: self._refresh_outlier_readouts()
        )
        self.fatigue_penalty_label = self._add_readout(grid, 6, 0, "FATIGUE PENALTY")
        self.natural_healing_label = self._add_readout(grid, 8, 0, "NATURAL HEALING")
        parent_layout.addWidget(section)

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

    def _add_readout(self, grid, row, column, caption, value="—"):
        """A small caption over a value; returns the value label."""
        value_label = self._role_label(value, "readout")
        value_label.setWordWrap(True)
        grid.addWidget(self._role_label(caption, "caption"), row, column)
        grid.addWidget(value_label, row + 1, column)
        return value_label

    @staticmethod
    def _role_label(text, role, center=False):
        """A label styled by its role in theme.SHEET_STYLE."""
        label = QLabel(text)
        label.setProperty("role", role)
        label.setIndent(0)
        if center:
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        return label

    @staticmethod
    def _new_rule(role, height):
        rule = QFrame()
        rule.setProperty("role", role)
        rule.setFixedHeight(height)
        return rule

    @staticmethod
    def _new_tile():
        tile = QFrame()
        tile.setProperty("role", "tile")
        return tile

    @staticmethod
    def _new_section(title):
        section = QWidget()
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(InteractiveCharacterSheet._role_label(title, "section-title"))
        layout.addWidget(InteractiveCharacterSheet._new_rule("section-rule", 2))
        layout.addSpacing(4)
        grid = QGridLayout()
        layout.addLayout(grid)
        return section, grid

    @staticmethod
    def _summary_html(entries):
        """Rich text for sheet entries: the name in bold, its details quieter below."""
        blocks = []
        for entry in entries:
            head, *rest = str(entry).split("\n")
            name, _, stats = head.partition(" - ")
            details = [stats] if stats else []
            details += [line.strip() for line in rest]
            block = f"<b>{html.escape(name, quote=False)}</b>"
            for line in details:
                block += (
                    f"<br><span style='color:{theme.SHEET_TEXT_MUTED};'>"
                    f"{html.escape(line, quote=False)}</span>"
                )
            blocks.append(f"<p style='margin:0 0 6px 0;'>{block}</p>")
        return "".join(blocks) or "None"

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
