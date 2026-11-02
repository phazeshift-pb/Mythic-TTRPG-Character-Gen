"""Light & Sky page of the interactive character sheet.

Tracks Light Energy and Super Energy, and shows every Aspect, Light Ability and
Super slot as a tile. Slots not yet bought for XP show as "Locked".
The rules live in src.models.light_loadout; this module only draws them.
"""
from __future__ import annotations

import html
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from src.loot.character_loot import element_icon
from src.models.light_loadout import LightLoadout, Power, Slot

EMPTY = "— Empty —"
SLOT_COLUMNS = 3
TILE_MIN_WIDTH = 240
TILE_MIN_HEIGHT = 190


def _label(text: str, role: str = "", wrap: bool = False, center: bool = False) -> QLabel:
    label = QLabel(text)
    if role:
        label.setProperty("role", role)
    label.setIndent(0)
    label.setWordWrap(wrap)
    if center:
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


def _section(title: str):
    """Heading + rule, matching the rest of the sheet. Returns (section, body layout)."""
    section = QWidget()
    layout = QVBoxLayout(section)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(4)
    layout.addWidget(_label(title, "section-title"))
    rule = QFrame()
    rule.setProperty("role", "section-rule")
    rule.setFixedHeight(2)
    layout.addWidget(rule)
    layout.addSpacing(4)
    body = QVBoxLayout()
    body.setSpacing(8)
    layout.addLayout(body)
    return section, body


def _clear(layout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()
        elif item.layout() is not None:
            _clear(item.layout())
            item.layout().deleteLater()


class LightAndSkyPage(QWidget):
    """Energy pools and slot tiles for one Light & Sky character."""

    loadout_changed = Signal()  # an Aspect went in or out (movement may change)
    unlock_requested = Signal()  # open the XP Shop to buy a slot

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character: dict[str, Any] = {}
        self.game_data = None
        self.ruleset = "Light & Sky"
        self.loadout: Optional[LightLoadout] = None
        self.slot_tiles: dict[str, list[QFrame]] = {"aspect": [], "ability": [], "super": []}
        self.slot_combos: dict[tuple[str, int], QComboBox] = {}
        self.use_buttons: dict[tuple[str, int], QPushButton] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(18)
        layout.addWidget(self._build_overview())
        layout.addWidget(self._build_energy())

        super_section, super_body = _section("Super")
        self.super_layout = QHBoxLayout()
        self.super_layout.setSpacing(10)
        super_body.addLayout(self.super_layout)
        layout.addWidget(super_section)

        ability_section, ability_body = _section("Light Ability Slots")
        self.ability_note = _label("", "note", wrap=True)
        ability_body.addWidget(self.ability_note)
        self.ability_grid = QGridLayout()
        self.ability_grid.setSpacing(10)
        ability_body.addLayout(self.ability_grid)
        layout.addWidget(ability_section)

        aspect_section, aspect_body = _section("Aspect Slots")
        self.aspect_note = _label("", "note", wrap=True)
        aspect_body.addWidget(self.aspect_note)
        self.aspect_grid = QGridLayout()
        self.aspect_grid.setSpacing(10)
        aspect_body.addLayout(self.aspect_grid)
        layout.addWidget(aspect_section)

        rules_section, rules_body = _section("Light Rules")
        self.rules_label = _label("", "note", wrap=True)
        self.rules_label.setTextFormat(Qt.TextFormat.RichText)
        rules_body.addWidget(self.rules_label)
        layout.addWidget(rules_section)
        layout.addStretch(1)

    # -----------------------------------------------------------------
    # Building
    # -----------------------------------------------------------------
    def _build_overview(self):
        section, body = _section("Guardian")
        grid = QGridLayout()
        grid.setHorizontalSpacing(28)
        self.class_label = _label("—", "form-line", wrap=True)
        self.connections_row = QHBoxLayout()
        self.connections_row.setSpacing(12)
        self.slot_summary_label = _label("—", "form-line", wrap=True)
        self.unslotted_label = _label("None", "note", wrap=True)
        grid.addWidget(_label("CLASS", "caption"), 0, 0)
        grid.addWidget(self.class_label, 1, 0)
        grid.addWidget(_label("CONNECTIONS", "caption"), 0, 1)
        grid.addLayout(self.connections_row, 1, 1)
        grid.addWidget(_label("SLOTS UNLOCKED", "caption"), 0, 2)
        grid.addWidget(self.slot_summary_label, 1, 2)
        grid.addWidget(_label("OWNED BUT NOT SLOTTED", "caption"), 2, 0, 1, 3)
        grid.addWidget(self.unslotted_label, 3, 0, 1, 3)
        for column in range(3):
            grid.setColumnStretch(column, 1)
        body.addLayout(grid)
        return section

    def _build_energy(self):
        section, body = _section("Energy")
        pools = QHBoxLayout()
        pools.setSpacing(14)
        self.energy_bars: dict[str, QProgressBar] = {}
        self.energy_inputs: dict[str, QSpinBox] = {}
        self.energy_values: dict[str, QLabel] = {}
        for pool, title, role in (
            ("light", "LIGHT ENERGY", "light-energy"),
            ("super", "SUPER ENERGY", "super-energy"),
        ):
            tile = QFrame()
            tile.setProperty("role", "tile")
            tile_layout = QVBoxLayout(tile)
            tile_layout.setContentsMargins(12, 10, 12, 10)
            tile_layout.setSpacing(6)
            head = QHBoxLayout()
            head.addWidget(_label(title, "caption"))
            head.addStretch(1)
            value = _label("—", "energy-value")
            head.addWidget(value)
            tile_layout.addLayout(head)
            bar = QProgressBar()
            bar.setProperty("role", role)
            bar.setTextVisible(False)
            bar.setFixedHeight(16)
            tile_layout.addWidget(bar)
            controls = QHBoxLayout()
            controls.setSpacing(6)
            spin = QSpinBox()
            spin.setKeyboardTracking(False)
            spin.setMinimumWidth(80)
            spin.valueChanged.connect(lambda amount, pool=pool: self._set_energy(pool, amount))
            controls.addWidget(_label("Current", "note"))
            controls.addWidget(spin)
            controls.addStretch(1)
            for step in (-10, -5, 5, 10):
                button = QPushButton(f"{step:+d}")
                button.setFixedWidth(44)
                button.clicked.connect(
                    lambda _=False, pool=pool, step=step: self._adjust_energy(pool, step)
                )
                controls.addWidget(button)
            tile_layout.addLayout(controls)
            self.energy_bars[pool] = bar
            self.energy_inputs[pool] = spin
            self.energy_values[pool] = value
            pools.addWidget(tile, 1)
        body.addLayout(pools)

        regen = QHBoxLayout()
        regen.setSpacing(6)
        regen.addWidget(_label("REGAIN", "caption"))
        self.regen_buttons: dict[str, QPushButton] = {}
        self.regen_row = regen
        self._regen_insert_at = regen.count()
        self.refill_button = QPushButton("Refill Both")
        self.refill_button.setToolTip("Set Light Energy and Super Energy to their maximum.")
        self.refill_button.clicked.connect(self._refill)
        regen.addWidget(self.refill_button)
        regen.addStretch(1)
        body.addLayout(regen)
        self.status_label = _label("", "note", wrap=True)
        body.addWidget(self.status_label)
        return section

    # -----------------------------------------------------------------
    # Loading
    # -----------------------------------------------------------------
    def set_character(self, character: dict[str, Any], game_data=None, ruleset: str = "Light & Sky"):
        """Show a character. ``character`` is edited in place as the player plays."""
        self.character = character
        self.game_data = game_data
        self.ruleset = ruleset
        self.loadout = LightLoadout(character, game_data, ruleset)
        self.status_label.setText("")
        self._build_regen_buttons()
        self._refresh_overview()
        self._refresh_energy()
        self._refresh_slots()
        self._refresh_rules()

    def _build_regen_buttons(self):
        for button in self.regen_buttons.values():
            self.regen_row.removeWidget(button)
            button.deleteLater()
        self.regen_buttons = {}
        for offset, (name, light, super_, rule) in enumerate(self.loadout.regeneration_events()):
            gains = []
            if light:
                gains.append(f"+{light} LE")
            if super_:
                gains.append(f"+{super_} SE")
            button = QPushButton(f"{name} ({', '.join(gains)})")
            button.setToolTip(rule)
            button.clicked.connect(
                lambda _=False, name=name, light=light, super_=super_: self._regenerate(name, light, super_)
            )
            self.regen_row.insertWidget(self._regen_insert_at + offset, button)
            self.regen_buttons[name] = button

    def _refresh_overview(self):
        self.class_label.setText(str(self.character.get("soldier_type") or "—"))
        _clear(self.connections_row)
        connections = [name for name in self.character.get("connections") or [] if name]
        if not connections:
            self.connections_row.addWidget(_label("None", "form-line"))
        for name in connections:
            chip = QHBoxLayout()
            chip.setSpacing(4)
            path = element_icon(name)
            if path:
                icon = QLabel()
                icon.setPixmap(QIcon(path).pixmap(18, 18))
                chip.addWidget(icon)
            chip.addWidget(_label(str(name), "form-line"))
            self.connections_row.addLayout(chip)
        self.connections_row.addStretch(1)

        loadout = self.loadout
        self.slot_summary_label.setText(
            f"Aspects {loadout.aspect_slot_count()}/{loadout.aspect_slot_maximum()}  ·  "
            f"Abilities {loadout.ability_slot_count()}/{loadout.ability_slot_maximum()}  ·  "
            "Super 1/1"
        )
        state = loadout.loadout()
        equipped = {str(name).casefold() for name in state["aspects"] + state["abilities"] if name}
        if state["super"]:
            equipped.add(state["super"].casefold())
        unslotted = [
            name
            for name in loadout.owned_aspects() + loadout.owned_abilities() + loadout.owned_supers()
            if name.casefold() not in equipped
        ]
        self.unslotted_label.setText(", ".join(unslotted) or "None - everything owned is slotted.")

    def _refresh_energy(self):
        for pool in ("light", "super"):
            maximum = self.loadout.maximum(pool)
            value = self.loadout.energy(pool)
            spin = self.energy_inputs[pool]
            spin.blockSignals(True)
            spin.setRange(0, maximum)
            spin.setValue(value)
            spin.blockSignals(False)
            bar = self.energy_bars[pool]
            bar.setRange(0, maximum)
            bar.setValue(value)
            self.energy_values[pool].setText(f"{value} / {maximum}")
        self._refresh_use_buttons()

    def _refresh_slots(self):
        self.slot_combos = {}
        self.use_buttons = {}
        loadout = self.loadout
        _clear(self.super_layout)
        self.slot_tiles = {"aspect": [], "ability": [], "super": []}
        for slot in loadout.slots("super"):
            tile = self._slot_tile(slot)
            self.super_layout.addWidget(tile, 2)
            self.slot_tiles["super"].append(tile)
        self.super_layout.addStretch(1)

        for kind, grid in (("ability", self.ability_grid), ("aspect", self.aspect_grid)):
            _clear(grid)
            for index, slot in enumerate(loadout.slots(kind)):
                tile = self._slot_tile(slot)
                row, column = divmod(index, SLOT_COLUMNS)
                grid.addWidget(tile, row, column)
                self.slot_tiles[kind].append(tile)
            for column in range(SLOT_COLUMNS):
                grid.setColumnStretch(column, 1)

        rules = loadout.ability_rules.get("rules", {})
        self.ability_note.setText(
            " ".join(
                text
                for text in (
                    rules.get("default_action", ""),
                    "Light Grenades also fill Light Ability Slots.",
                    rules.get("ability_slots", {}).get("between_missions", ""),
                )
                if text
            )
        )
        self.aspect_note.setText(
            loadout.aspect_rules.get("aspect_slots", {}).get("between_missions", "")
            or "Aspects are passive while slotted."
        )
        self._refresh_use_buttons()

    def _refresh_rules(self):
        rules = self.loadout.ability_rules
        lines = []
        for title, text in (
            ("Supers", rules.get("supers", {}).get("energy_cost", "")),
            ("One Super", rules.get("supers", {}).get("availability", "")),
            ("Grenade Supers", rules.get("grenade_supers", {}).get("rule", "")),
            ("Double Jump", rules.get("double_jump", {}).get("description", "")),
            ("Double Jump limits", rules.get("double_jump", {}).get("limitations", "")),
            ("Falling", rules.get("double_jump", {}).get("falling_damage", "")),
        ):
            if text:
                lines.append(f"<b>{html.escape(title)}:</b> {html.escape(text)}")
        self.rules_label.setText("<br>".join(lines))

    # -----------------------------------------------------------------
    # Tiles
    # -----------------------------------------------------------------
    def _slot_tile(self, slot: Slot) -> QFrame:
        tile = QFrame()
        tile.setMinimumSize(TILE_MIN_WIDTH, TILE_MIN_HEIGHT)
        layout = QVBoxLayout(tile)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)
        title = {"aspect": "ASPECT SLOT", "ability": "ABILITY SLOT", "super": "SUPER"}[slot.kind]
        head = QHBoxLayout()
        head.addWidget(_label(title if slot.kind == "super" else f"{title} {slot.number}", "caption"))
        head.addStretch(1)
        layout.addLayout(head)

        if not slot.unlocked:
            tile.setProperty("role", "slot-locked")
            tile.setObjectName(f"{slot.kind}SlotLocked{slot.number}")
            layout.addStretch(1)
            layout.addWidget(_label("LOCKED", "slot-locked-title", center=True))
            cost = f"Unlock for {slot.unlock_cost:,} XP" if slot.unlock_cost else "Unlock in the XP Shop"
            layout.addWidget(_label(cost, "note", center=True))
            button = QPushButton("Open XP Shop")
            button.setToolTip(
                slot.unlock_note or "Buy this slot under Light Slots in the XP Shop."
            )
            button.setEnabled(not slot.unlock_note)
            button.clicked.connect(lambda _=False: self.unlock_requested.emit())
            if slot.unlock_note:
                layout.addWidget(_label(slot.unlock_note, "note", center=True))
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignHCenter)
            layout.addStretch(1)
            return tile

        power = self.loadout.power(slot.equipped) if slot.equipped else None
        if slot.kind == "super":
            tile.setProperty("role", "slot-super")
        else:
            tile.setProperty("role", "slot-filled" if power else "slot")
        tile.setObjectName(f"{slot.kind}Slot{slot.number}")

        combo = QComboBox()
        combo.addItem(EMPTY, None)
        for name in self.loadout.available_for(slot.kind, slot.number):
            combo.addItem(name, name)
        if slot.equipped:
            combo.setCurrentIndex(max(0, combo.findData(slot.equipped)))
        combo.currentIndexChanged.connect(
            lambda _index, kind=slot.kind, number=slot.number, combo=combo: self._equip(
                kind, number, combo.currentData()
            )
        )
        self.slot_combos[(slot.kind, slot.number)] = combo
        layout.addWidget(combo)

        if power is None:
            owned = {
                "aspect": self.loadout.owned_aspects,
                "ability": self.loadout.owned_abilities,
                "super": self.loadout.owned_supers,
            }[slot.kind]()
            hint = (
                "Empty slot. Pick an owned power above."
                if owned
                else "Nothing owned yet. Buy one in the XP Shop."
            )
            layout.addWidget(_label(hint, "note", wrap=True))
            layout.addStretch(1)
            return tile

        as_super = slot.kind == "super"
        details = QHBoxLayout()
        details.setSpacing(4)
        path = element_icon(power.connection)
        if path:
            icon = QLabel()
            icon.setPixmap(QIcon(path).pixmap(16, 16))
            details.addWidget(icon)
        detail_parts = [power.connection, power.category or power.kind]
        if power.guardian_class and power.guardian_class.casefold() != "all":
            detail_parts.append(power.guardian_class)
        details.addWidget(_label(" · ".join(part for part in detail_parts if part), "note"))
        details.addStretch(1)
        if slot.kind != "aspect":
            badge_role = "super-badge" if as_super else "energy-badge"
            details.addWidget(
                _label(power.energy_text(as_super, self.loadout.super_energy_multiplier), badge_role)
            )
        layout.addLayout(details)

        description = (power.super_description or power.description) if as_super else power.description
        if power.stats:
            layout.addWidget(_label("  ·  ".join(power.stats), "strong", wrap=True))
        text = _label(description or "No description.", "", wrap=True)
        text.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(text, 1)
        tooltip = [description]
        if not as_super and power.super_description and power.kind != "Light Aspect":
            tooltip.append(f"As a Super: {power.super_description}")
        tile.setToolTip("\n\n".join(part for part in tooltip if part))

        if slot.kind != "aspect":
            cost = power.energy_cost(as_super, self.loadout.super_energy_multiplier)
            verb = "Cast Super" if as_super else "Use"
            button = QPushButton(f"{verb} (-{cost})" if cost is not None else verb)
            button.setProperty("energy_cost", cost)
            button.clicked.connect(
                lambda _=False, kind=slot.kind, number=slot.number: self._use(kind, number)
            )
            self.use_buttons[(slot.kind, slot.number)] = button
            layout.addWidget(button, 0, Qt.AlignmentFlag.AlignRight)
        return tile

    def _refresh_use_buttons(self):
        if self.loadout is None:
            return
        for (kind, _number), button in self.use_buttons.items():
            cost = button.property("energy_cost")
            pool = "super" if kind == "super" else "light"
            if cost is None:
                button.setEnabled(True)
                button.setToolTip("Energy cost varies: adjust the energy by hand.")
                continue
            enough = self.loadout.energy(pool) >= cost
            button.setEnabled(enough)
            button.setToolTip(
                "" if enough else f"Not enough {'Super' if pool == 'super' else 'Light'} Energy"
            )

    # -----------------------------------------------------------------
    # Actions
    # -----------------------------------------------------------------
    def _equip(self, kind: str, number: int, name: Optional[str]):
        if self.loadout is None:
            return
        self.loadout.equip(kind, number, name)
        self._refresh_overview()
        self._refresh_slots()
        if kind == "aspect":
            self.loadout_changed.emit()

    def _use(self, kind: str, number: int):
        state = self.loadout.loadout()
        name = state["super"] if kind == "super" else state["abilities"][number - 1]
        if not name:
            return
        power: Power = self.loadout.power(name)
        as_super = kind == "super"
        pool = "super" if as_super else "light"
        cost = power.energy_cost(as_super, self.loadout.super_energy_multiplier)
        pool_name = "Super Energy" if as_super else "Light Energy"
        if cost is None:
            self._status(f"{name}: cost varies - adjust {pool_name} by hand.")
            return
        if not self.loadout.spend(pool, cost):
            self._status(f"Not enough {pool_name} for {name} ({cost} needed).", bad=True)
            return
        self._refresh_energy()
        self._status(f"{'Cast' if as_super else 'Used'} {name}: -{cost} {pool_name}.")

    def _set_energy(self, pool: str, value: int):
        if self.loadout is None:
            return
        self.loadout.set_energy(pool, value)
        self._refresh_energy()

    def _adjust_energy(self, pool: str, step: int):
        self.loadout.set_energy(pool, self.loadout.energy(pool) + step)
        self._refresh_energy()

    def _regenerate(self, name: str, light: int, super_: int):
        light_value, super_value = self.loadout.gain(light, super_)
        self._refresh_energy()
        self._status(f"{name}: Light Energy {light_value}, Super Energy {super_value}.", good=True)

    def _refill(self):
        for pool in ("light", "super"):
            self.loadout.set_energy(pool, self.loadout.maximum(pool))
        self._refresh_energy()
        self._status("Energy refilled.", good=True)

    def _status(self, text: str, bad: bool = False, good: bool = False):
        self.status_label.setProperty("role", "status-bad" if bad else "status-good" if good else "note")
        self.status_label.style().unpolish(self.status_label)
        self.status_label.style().polish(self.status_label)
        self.status_label.setText(text)
