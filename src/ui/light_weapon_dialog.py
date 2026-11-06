"""Light Weapon builder dialog (Light & Sky Universal Weapon Ability).

Opens when a player takes the Light Weapon ability, as a Light Ability or as a
Super, in the creator or the XP Shop. The player picks the weapon it is based
on, the Connection it is made of and up to 4 effects; the dialog shows the
Light Cost, Energy per Turn and the weapon's modified stats as they choose.

``LightWeaponBuilderDialog.result_build()`` returns the build dict to save
(see src/models/light_weapon.py). The rules all live in that module.
"""
from __future__ import annotations

import html
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSpinBox,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models import light_weapon
from src.models.light_weapon import (
    CATEGORIES,
    MAX_EFFECT_COUNT,
    MAX_EFFECTS,
    RANGED,
    LightWeaponRules,
    WeaponChoice,
)

CATEGORY_LABELS = {
    light_weapon.MELEE: "Melee Weapons",
    light_weapon.SHIELD: "Physical Shields",
    light_weapon.RANGED: "Ranged Weapons (Emblem)",
}
WEAPON_ROLE = Qt.ItemDataRole.UserRole
EFFECT_ROLE = Qt.ItemDataRole.UserRole


class LightWeaponBuilderDialog(QDialog):
    """Build one Light Weapon: weapon, Connection, effects."""

    def __init__(
        self,
        game_data,
        character: dict,
        as_super: bool,
        parent=None,
        connections: Optional[list[str]] = None,
        build: Optional[dict] = None,
        taken_names=(),
    ):
        super().__init__(parent)
        self.rules = LightWeaponRules(game_data)
        self.character = character or {}
        self.as_super = bool(as_super)
        self.taken_names = list(taken_names)
        self._result: Optional[dict] = None
        self._name_edited = False
        self._effect_rows: list[tuple[light_weapon.Effect, QTableWidgetItem, Optional[QSpinBox]]] = []
        connections = connections or self.rules.connection_options(self.character)

        kind = "Super" if self.as_super else "Light Ability"
        self.setWindowTitle(f"Light Weapon Builder - {kind}")
        self.setMinimumSize(980, 640)

        layout = QVBoxLayout(self)
        intro = QLabel(self._intro_text())
        intro.setWordWrap(True)
        layout.addWidget(intro)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(self._build_weapon_panel())
        splitter.addWidget(self._build_effect_panel(connections))
        splitter.addWidget(self._build_summary_panel())
        splitter.setSizes([300, 400, 300])
        layout.addWidget(splitter, 1)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText(
            f"Create {kind}"
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self._fill_weapons()
        self._fill_effects()
        if build:
            self._load_build(build)
        self._refresh()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _intro_text(self) -> str:
        if self.as_super:
            return (
                "As a Super the weapon gains +2D10 Damage Dice and up to "
                f"{MAX_EFFECTS} effects. It spends double its Light Cost in Super Energy "
                "each Turn it is active, plus each effect's listed Energy."
            )
        return (
            "The weapon gains +1D10 Damage Dice, deals Special Damage on 9 or 10, and adds "
            "your Warfare modifier to Base Damage and Pierce. It spends its Light Cost in "
            f"Light Energy each Turn it is active. Up to {MAX_EFFECTS} effects can be added "
            "at double their listed Energy."
        )

    def _build_weapon_panel(self) -> QWidget:
        box = QGroupBox("1. Weapon")
        layout = QVBoxLayout(box)
        self.category_combo = QComboBox(box)
        for category in CATEGORIES:
            self.category_combo.addItem(CATEGORY_LABELS[category], category)
        self.category_combo.currentIndexChanged.connect(self._fill_weapons)
        layout.addWidget(self.category_combo)

        self.search_input = QLineEdit(box)
        self.search_input.setPlaceholderText("Search weapons")
        self.search_input.textChanged.connect(self._fill_weapons)
        layout.addWidget(self.search_input)

        self.weapon_list = QListWidget(box)
        self.weapon_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.weapon_list.currentItemChanged.connect(lambda *_: self._weapon_changed())
        layout.addWidget(self.weapon_list, 1)

        self.roll_row = QWidget(box)
        roll_layout = QHBoxLayout(self.roll_row)
        roll_layout.setContentsMargins(0, 0, 0, 0)
        roll_layout.addWidget(QLabel("Roll table row"))
        self.row_combo = QComboBox(self.roll_row)
        for index in range(len(light_weapon.ROLL_BANDS)):
            self.row_combo.addItem(LightWeaponRules.roll_band(index), index)
        self.row_combo.currentIndexChanged.connect(self._refresh)
        roll_layout.addWidget(self.row_combo, 1)
        self.roll_button = QPushButton("Roll 1D100", self.roll_row)
        self.roll_button.clicked.connect(self._roll)
        roll_layout.addWidget(self.roll_button)
        layout.addWidget(self.roll_row)
        self.roll_note = QLabel("", box)
        layout.addWidget(self.roll_note)
        return box

    def _build_effect_panel(self, connections: list[str]) -> QWidget:
        box = QGroupBox("2. Connection and effects")
        layout = QVBoxLayout(box)
        form = QFormLayout()
        self.connection_combo = QComboBox(box)
        for connection in connections:
            self.connection_combo.addItem(connection, connection)
        self.connection_combo.currentIndexChanged.connect(self._connection_changed)
        form.addRow("Connection", self.connection_combo)
        self.name_input = QLineEdit(box)
        self.name_input.textEdited.connect(self._name_was_edited)
        form.addRow("Name", self.name_input)
        layout.addLayout(form)

        note = (
            "Universal effects plus the chosen Connection's."
            if not self.rules.has_prismatic(self.character)
            else "Prismatic: effects from any of your Connections can be mixed."
        )
        self.effect_note = QLabel(note, box)
        self.effect_note.setWordWrap(True)
        layout.addWidget(self.effect_note)

        self.effect_table = QTableWidget(0, 3, box)
        self.effect_table.setHorizontalHeaderLabels(["Effect", "Energy", "Count"])
        header = self.effect_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.effect_table.verticalHeader().setVisible(False)
        self.effect_table.setWordWrap(True)
        self.effect_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.effect_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.effect_table.itemChanged.connect(self._effect_toggled)
        layout.addWidget(self.effect_table, 1)
        self.effect_count = QLabel("", box)
        layout.addWidget(self.effect_count)
        return box

    def _build_summary_panel(self) -> QWidget:
        box = QGroupBox("3. Summary")
        layout = QVBoxLayout(box)
        self.summary = QLabel("", box)
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        self.summary.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(self.summary, 1)
        self.problem_label = QLabel("", box)
        self.problem_label.setWordWrap(True)
        self.problem_label.setStyleSheet("color: #f0907a;")
        layout.addWidget(self.problem_label)
        return box

    # ------------------------------------------------------------------
    # Filling
    # ------------------------------------------------------------------
    def _fill_weapons(self, *_):
        selected = self.selected_weapon()
        category = self.category_combo.currentData()
        query = self.search_input.text().strip().casefold()
        self.weapon_list.blockSignals(True)
        self.weapon_list.clear()
        group = None
        restore = None
        for weapon in self.rules.weapons(category):
            if query and query not in f"{weapon.name} {weapon.group}".casefold():
                continue
            if weapon.group != group and category != RANGED:
                group = weapon.group
                header = QListWidgetItem(group.upper())
                header.setFlags(Qt.ItemFlag.NoItemFlags)
                font = QFont(header.font())
                font.setBold(True)
                header.setFont(font)
                self.weapon_list.addItem(header)
            item = QListWidgetItem(
                f"{weapon.name}  —  {weapon.cost_cr} cR → Light Cost {weapon.light_cost}"
            )
            item.setData(WEAPON_ROLE, weapon.key)
            self.weapon_list.addItem(item)
            if selected is not None and weapon.key == selected.key:
                restore = item
        self.weapon_list.blockSignals(False)
        if restore is not None:
            self.weapon_list.setCurrentItem(restore)
        self.roll_row.setVisible(category == RANGED)
        self.roll_note.setVisible(category == RANGED)
        self._weapon_changed()

    def _fill_effects(self):
        checked = {key: count for key, count in self.selected_effects()}
        connection = self.connection_combo.currentData() or ""
        self.effect_table.blockSignals(True)
        self.effect_table.setRowCount(0)
        self._effect_rows = []
        current = None
        for effect in self.rules.effects_for(connection, self.character):
            if effect.connection != current:
                current = effect.connection
                row = self.effect_table.rowCount()
                self.effect_table.insertRow(row)
                header = QTableWidgetItem(current.upper())
                header.setFlags(Qt.ItemFlag.ItemIsEnabled)
                font = QFont(header.font())
                font.setBold(True)
                header.setFont(font)
                self.effect_table.setItem(row, 0, header)
                self.effect_table.setSpan(row, 0, 1, 3)
            row = self.effect_table.rowCount()
            self.effect_table.insertRow(row)
            item = QTableWidgetItem(effect.description)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if effect.key in checked else Qt.CheckState.Unchecked
            )
            item.setData(EFFECT_ROLE, effect.key)
            item.setToolTip(effect.description)
            self.effect_table.setItem(row, 0, item)
            energy = QTableWidgetItem(self._energy_label(effect))
            energy.setFlags(Qt.ItemFlag.ItemIsEnabled)
            self.effect_table.setItem(row, 1, energy)
            spin = None
            if effect.counted:
                spin = QSpinBox(self.effect_table)
                spin.setRange(1, MAX_EFFECT_COUNT)
                spin.setValue(checked.get(effect.key, 1))
                spin.setToolTip(effect.per)
                spin.valueChanged.connect(self._refresh)
                self.effect_table.setCellWidget(row, 2, spin)
            self._effect_rows.append((effect, item, spin))
        self.effect_table.blockSignals(False)
        self.effect_table.resizeRowsToContents()

    def _energy_label(self, effect) -> str:
        energy = effect.energy if self.as_super else effect.energy * 2
        each = f" {effect.per.lower()}" if effect.per else ""
        return f"+{energy}{each}"

    def _load_build(self, build: dict):
        weapon = build.get("weapon") or {}
        choice = self.rules.weapon(weapon.get("key", ""))
        if choice is not None:
            self.category_combo.setCurrentIndex(self.category_combo.findData(choice.category))
            for row in range(self.weapon_list.count()):
                if self.weapon_list.item(row).data(WEAPON_ROLE) == choice.key:
                    self.weapon_list.setCurrentRow(row)
                    break
            if weapon.get("row_index") is not None:
                self.row_combo.setCurrentIndex(int(weapon["row_index"]))
        index = self.connection_combo.findData(build.get("connection"))
        if index >= 0:
            self.connection_combo.setCurrentIndex(index)
        wanted = {effect.get("key"): effect.get("count", 1) for effect in build.get("effects") or []}
        self.effect_table.blockSignals(True)
        for effect, item, spin in self._effect_rows:
            if effect.key in wanted:
                item.setCheckState(Qt.CheckState.Checked)
                if spin is not None:
                    spin.setValue(int(wanted[effect.key] or 1))
        self.effect_table.blockSignals(False)
        if build.get("name"):
            self.name_input.setText(build["name"])
            self._name_edited = True

    # ------------------------------------------------------------------
    # Reactions
    # ------------------------------------------------------------------
    def _weapon_changed(self):
        self._update_default_name()
        self._refresh()

    def _connection_changed(self, *_):
        self._fill_effects()
        self._update_default_name()
        self._refresh()

    def _name_was_edited(self, text):
        self._name_edited = bool(text.strip())

    def _update_default_name(self):
        if self._name_edited:
            return
        weapon = self.selected_weapon()
        connection = self.connection_combo.currentData() or ""
        self.name_input.setText(
            self.rules.default_name(weapon, connection, self.as_super) if weapon is not None else ""
        )

    def _effect_toggled(self, item):
        if item.column() == 0:
            self._refresh()

    def _roll(self):
        roll, index = LightWeaponRules.roll_row()
        self.row_combo.setCurrentIndex(index)
        self.roll_note.setText(f"Rolled {roll}: row {LightWeaponRules.roll_band(index)}")

    # ------------------------------------------------------------------
    # State
    # ------------------------------------------------------------------
    def selected_weapon(self) -> Optional[WeaponChoice]:
        item = self.weapon_list.currentItem() if hasattr(self, "weapon_list") else None
        key = item.data(WEAPON_ROLE) if item is not None else None
        return self.rules.weapon(key) if key else None

    def selected_effects(self) -> list[tuple[str, int]]:
        return [
            (effect.key, spin.value() if spin is not None else 1)
            for effect, item, spin in self._effect_rows
            if item.checkState() == Qt.CheckState.Checked
        ]

    def _row_index(self) -> Optional[int]:
        weapon = self.selected_weapon()
        return self.row_combo.currentData() if weapon is not None and weapon.is_ranged else None

    def _current_build(self) -> tuple[Optional[dict], list[str]]:
        weapon = self.selected_weapon()
        connection = self.connection_combo.currentData() or ""
        if weapon is None:
            return None, ["Choose a weapon."]
        try:
            build = self.rules.build(
                weapon,
                connection,
                self.as_super,
                self.selected_effects(),
                row_index=self._row_index(),
                character=self.character,
                name=self.name_input.text().strip(),
            )
        except ValueError as error:
            return None, [str(error)]
        build["name"] = light_weapon.unique_name(self.character, build["name"], self.taken_names)
        return build, []

    def _refresh(self, *_):
        if not hasattr(self, "summary"):
            return
        chosen = len(self.selected_effects())
        self.effect_table.blockSignals(True)
        for _effect, item, spin in self._effect_rows:
            is_checked = item.checkState() == Qt.CheckState.Checked
            enabled = is_checked or chosen < MAX_EFFECTS
            flags = Qt.ItemFlag.ItemIsUserCheckable | (
                Qt.ItemFlag.ItemIsEnabled if enabled else Qt.ItemFlag.NoItemFlags
            )
            item.setFlags(flags)
            if spin is not None:
                spin.setEnabled(is_checked)
        self.effect_table.blockSignals(False)
        self.effect_count.setText(f"Effects chosen: {chosen} / {MAX_EFFECTS}")

        build, problems = self._current_build()
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(build is not None)
        self.problem_label.setText(" ".join(problems))
        self.summary.setText(self._summary_html(build) if build else "Choose a weapon to see its cost and stats.")

    def _summary_html(self, build: dict) -> str:
        pool = "Super Energy" if self.as_super else "Light Energy"
        stats = build["stats"]
        effects_energy = self.rules.effects_energy(build["effects"], self.as_super)
        base_energy = build["energy_per_turn"] - effects_energy
        parts = [
            f"<b>{html.escape(build['name'])}</b>",
            f"{html.escape(build['connection'])} · {html.escape(build['weapon']['category'])}"
            + (f" · roll {build['weapon']['roll']}" if build["weapon"].get("roll") else ""),
            "",
            f"<b>XP cost:</b> {build['experience_cost']:,}",
            f"<b>Light Cost:</b> {build['light_cost']} "
            f"({build['weapon']['cost_cr']} cR rounded up to 5)",
            f"<b>{pool} per Turn:</b> {build['energy_per_turn']}"
            f" &nbsp;<i>({base_energy} weapon + {effects_energy} effects)</i>",
            "",
            f"<b>Damage:</b> {html.escape(str(stats['damage']))} "
            f"+{html.escape(str(stats['bonus_damage']))}",
            f"<b>Pierce:</b> {html.escape(str(stats['pierce']))}",
        ]
        if stats.get("warfare_modifier") is None:
            parts.append(
                f"<i>{stats['warfare']} modifier not known here; add it at the table.</i>"
            )
        for field_name, label in (
            ("reach", "Reach"), ("range", "Range"), ("rate_of_fire", "Rate of Fire"),
            ("magazine", "Magazine"), ("shield_armor", "Shield Armor"),
            ("breakpoints", "Breakpoints"),
        ):
            if stats.get(field_name) not in (None, ""):
                parts.append(f"<b>{label}:</b> {html.escape(str(stats[field_name]))}")
        if stats.get("tags"):
            parts.append("<b>Tags:</b> " + " ".join(f"[{t}]" for t in stats["tags"]))
        if stats.get("special_rules"):
            parts.append("<b>Rules:</b> " + html.escape(", ".join(stats["special_rules"])))
        if build["effects"]:
            parts.append("")
            parts.append("<b>Effects</b>")
            for effect in build["effects"]:
                count = f" ×{effect['count']}" if effect.get("per") else ""
                parts.append(
                    f"• {html.escape(effect['description'])}{count} "
                    f"<i>({html.escape(effect['connection'])})</i>"
                )
        return "<br>".join(parts)

    # ------------------------------------------------------------------
    # Result
    # ------------------------------------------------------------------
    def accept(self):
        build, problems = self._current_build()
        if build is None:
            self.problem_label.setText(" ".join(problems))
            return
        self._result = build
        super().accept()

    def result_build(self) -> Optional[dict]:
        return self._result


def build_light_weapon(game_data, character, as_super, parent=None, **kwargs) -> Optional[dict]:
    """Open the builder and return the new build, or None if cancelled."""
    dialog = LightWeaponBuilderDialog(game_data, character, as_super, parent, **kwargs)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        return dialog.result_build()
    return None
