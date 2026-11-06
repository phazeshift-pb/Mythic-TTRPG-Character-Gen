"""Light & Sky loot roller, opened from a Light & Sky character's sheet.

The randomizer from the Destiny TTRPG Loot Generator: pick weapons or armor,
optionally narrow by ammo type, weapon type, material and rarity, then
Generate. The rolled item is shown as a loot card that can be added to the
character (weapons) or equipped (armor), or exported as a PNG.

Roll logic lives in src/loot/generator.py; applying it to the character is
the sheet's job (``on_add``).
"""

from typing import Callable, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.loot.character_loot import loot_card_html, perk_descriptions
from src.loot.generator import AMMO_TYPES, ARMOR_MATERIALS, LootGenerator
from src.loot.loot_rules import RARITIES, RARITY_COLORS
from src.ui import theme

LOOT_CARD_WIDTH = 360
LOOT_CARD_MIN_HEIGHT = 640


class LootDialog(QDialog):
    def __init__(
        self,
        generator: LootGenerator,
        on_add: Optional[Callable[[dict], Optional[str]]] = None,
        parent=None,
    ):
        """``on_add(roll)`` applies the roll and returns a status message (None if cancelled)."""
        super().__init__(parent)
        self.generator = generator
        self.on_add = on_add
        self.current_roll: Optional[dict] = None

        self.setWindowTitle("Light & Sky Loot")
        self.setMinimumSize(820, 760)

        layout = QHBoxLayout(self)
        layout.setSpacing(16)

        # ---------- Options ----------
        options = QWidget()
        options.setFixedWidth(330)
        options_layout = QVBoxLayout(options)
        options_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel("Loot Generator")
        title.setStyleSheet(theme.PAGE_TITLE)
        options_layout.addWidget(title)

        form = QFormLayout()
        self.kind_combo = QComboBox()
        self.kind_combo.addItem("Weapon", "weapon")
        self.kind_combo.addItem("Armor", "armor")
        form.addRow("Item:", self.kind_combo)

        self.ammo_combo = QComboBox()
        self.ammo_combo.addItem("Any", None)
        for ammo in AMMO_TYPES:
            self.ammo_combo.addItem(ammo, ammo)
        self.ammo_label = QLabel("Ammo type:")
        form.addRow(self.ammo_label, self.ammo_combo)

        self.weapon_type_combo = QComboBox()
        self.weapon_type_label = QLabel("Weapon type:")
        form.addRow(self.weapon_type_label, self.weapon_type_combo)

        self.material_combo = QComboBox()
        self.material_combo.addItem("Random", None)
        for material in ARMOR_MATERIALS:
            self.material_combo.addItem(material.title(), material)
        self.material_label = QLabel("Material:")
        form.addRow(self.material_label, self.material_combo)

        self.rarity_combo = QComboBox()
        self.rarity_combo.addItem("Random", None)
        for rarity in RARITIES:
            self.rarity_combo.addItem(rarity, rarity)
        form.addRow("Rarity:", self.rarity_combo)
        options_layout.addLayout(form)

        self.generate_button = QPushButton("Generate")
        self.generate_button.setStyleSheet(theme.SELECT_BUTTON)
        self.generate_button.clicked.connect(self.generate)
        options_layout.addWidget(self.generate_button)

        self.status_label = QLabel()
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {theme.TEXT_MUTED}; padding: 6px 0;")
        options_layout.addWidget(self.status_label)
        options_layout.addStretch(1)
        layout.addWidget(options)

        # ---------- Loot card ----------
        card_column = QVBoxLayout()
        self.card_frame = QFrame()
        self.card_frame.setObjectName("lootCard")
        self.card_frame.setFixedWidth(LOOT_CARD_WIDTH)
        self.card_frame.setMinimumHeight(LOOT_CARD_MIN_HEIGHT)
        self._set_card_border("#ffffff")
        card_layout = QVBoxLayout(self.card_frame)
        card_layout.setContentsMargins(12, 12, 12, 12)
        self.card_label = QLabel("Choose your options and press Generate.")
        self.card_label.setWordWrap(True)
        self.card_label.setTextFormat(Qt.TextFormat.RichText)
        self.card_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.card_label.setStyleSheet("color: #171717; border: none;")
        card_layout.addWidget(self.card_label)
        card_scroll = QScrollArea()
        card_scroll.setWidgetResizable(True)
        card_scroll.setFrameShape(QFrame.Shape.NoFrame)
        card_scroll.setMinimumWidth(LOOT_CARD_WIDTH + 24)
        card_scroll.setWidget(self.card_frame)
        card_column.addWidget(card_scroll, stretch=1)

        actions = QHBoxLayout()
        self.add_button = QPushButton("Add to Weapons")
        self.add_button.setEnabled(False)
        self.add_button.clicked.connect(self.add_to_character)
        self.export_button = QPushButton("Export Card")
        self.export_button.setEnabled(False)
        self.export_button.clicked.connect(self.export_card)
        actions.addWidget(self.add_button)
        actions.addWidget(self.export_button)
        actions.addStretch(1)
        close_buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_buttons.rejected.connect(self.reject)
        actions.addWidget(close_buttons)
        card_column.addLayout(actions)
        layout.addLayout(card_column, stretch=1)

        self.kind_combo.currentIndexChanged.connect(self._update_visibility)
        self.ammo_combo.currentIndexChanged.connect(self._refresh_weapon_types)
        self._refresh_weapon_types()
        self._update_visibility()

    # ---------------------------------------------------------
    # Options
    # ---------------------------------------------------------
    @property
    def selected_kind(self) -> str:
        return self.kind_combo.currentData()

    def _update_visibility(self, *_):
        weapon = self.selected_kind == "weapon"
        for widget in (self.ammo_label, self.ammo_combo, self.weapon_type_label, self.weapon_type_combo):
            widget.setVisible(weapon)
        for widget in (self.material_label, self.material_combo):
            widget.setVisible(not weapon)

    def _refresh_weapon_types(self, *_):
        previous = self.weapon_type_combo.currentData()
        self.weapon_type_combo.blockSignals(True)
        self.weapon_type_combo.clear()
        self.weapon_type_combo.addItem("Random", "any")
        for label, key in self.generator.weapon_types(self.ammo_combo.currentData()):
            self.weapon_type_combo.addItem(label, key)
        index = self.weapon_type_combo.findData(previous)
        self.weapon_type_combo.setCurrentIndex(max(0, index))
        self.weapon_type_combo.blockSignals(False)

    # ---------------------------------------------------------
    # Rolling
    # ---------------------------------------------------------
    def generate(self):
        rarity = self.rarity_combo.currentData()
        try:
            if self.selected_kind == "weapon":
                roll = self.generator.generate_weapon(
                    self.weapon_type_combo.currentData() or "any",
                    forced_rarity=rarity,
                    ammo_type=self.ammo_combo.currentData(),
                )
            else:
                roll = self.generator.generate_armor(
                    self.material_combo.currentData(), forced_rarity=rarity
                )
        except ValueError as error:
            self.status_label.setText(str(error))
            return
        self.show_roll(roll)

    def show_roll(self, roll: dict):
        self.current_roll = roll
        self._set_card_border(RARITY_COLORS.get(roll.get("rarity"), "#ffffff"))
        self.card_label.setText(loot_card_html(roll))
        self.card_label.setToolTip(perk_descriptions(roll))
        weapon = roll.get("kind") == "weapon"
        self.add_button.setText("Add to Weapons" if weapon else "Equip Armor")
        self.add_button.setEnabled(self.on_add is not None)
        self.export_button.setEnabled(True)
        self.status_label.setText("Hover over the card to read the perk descriptions.")

    def _set_card_border(self, color: str):
        self.card_frame.setStyleSheet(
            f"QFrame#lootCard {{ background-color: #e9e7df; border: 3px solid {color}; border-radius: 3px; }}"
        )

    # ---------------------------------------------------------
    # Actions
    # ---------------------------------------------------------
    def add_to_character(self):
        if self.current_roll is None or self.on_add is None:
            return
        message = self.on_add(self.current_roll)
        if message:
            self.status_label.setText(message)
            self.add_button.setEnabled(False)  # one roll, one item

    def export_card(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export loot card", "exported_loot.png", "PNG images (*.png)"
        )
        if not file_path:
            return
        if not file_path.lower().endswith(".png"):
            file_path += ".png"
        if self.card_frame.grab().save(file_path):
            self.status_label.setText(f"Loot card exported to {file_path}")
        else:
            self.status_label.setText(f"Could not export loot card to {file_path}.")
