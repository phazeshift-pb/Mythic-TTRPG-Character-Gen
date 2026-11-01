from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)

from src.models import starting_armor
from src.models.equipment_packs import armor_summary


class StartingArmorDialog(QDialog):
    """Pick a Spartan's starting suit and, for Mjolnir, an optional variant."""

    NO_VARIANT = "None (standard suit)"

    def __init__(self, soldier_data, armors, game_data, selected=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Starting Armor")
        self.setMinimumWidth(520)
        self._soldier_data = soldier_data
        self._armors = armors
        self._game_data = game_data
        self._options = starting_armor.armor_options(soldier_data)
        self._variants = []
        selected = selected or {}

        layout = QVBoxLayout(self)
        intro = QLabel(
            "Spartans begin with Mjolnir or other armor suited to the timeline. "
            "Years show when each suit was in use; your GM may allow older armor or SPI. "
            "Mjolnir variants cost the listed cR to fit to your suit."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.armor_combo = QComboBox(self)
        for option in self._options:
            self.armor_combo.addItem(option.get("label") or option["armor"], option["armor"])
        form.addRow("Suit", self.armor_combo)
        self.variant_combo = QComboBox(self)
        form.addRow("Variant", self.variant_combo)
        layout.addLayout(form)

        self.details = QLabel(self)
        self.details.setWordWrap(True)
        self.details.setMinimumHeight(120)
        layout.addWidget(self.details)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.armor_combo.currentIndexChanged.connect(self._refresh_variants)
        self.variant_combo.currentIndexChanged.connect(self._refresh_details)

        index = self.armor_combo.findData(selected.get("armor"))
        self.armor_combo.setCurrentIndex(index if index >= 0 else 0)
        self._refresh_variants()
        previous = selected.get("variant") or {}
        for i, variant in enumerate(self._variants):
            if (variant["generation"], variant["name"]) == (
                previous.get("generation"),
                previous.get("name"),
            ):
                self.variant_combo.setCurrentIndex(i + 1)
                break

    def _refresh_variants(self):
        record = self._armors.get(self.selected_armor or "")
        self._variants = starting_armor.variants_for(record, self._game_data)
        self.variant_combo.blockSignals(True)
        self.variant_combo.clear()
        self.variant_combo.addItem(self.NO_VARIANT)
        for variant in self._variants:
            self.variant_combo.addItem(starting_armor.variant_label(variant))
        self.variant_combo.setEnabled(bool(self._variants))
        self.variant_combo.blockSignals(False)
        self._refresh_details()

    def _refresh_details(self):
        name = self.selected_armor
        lines = [armor_summary(name, self._armors)]
        bonus = starting_armor.format_bonus(
            starting_armor.worn_bonus(name, self._soldier_data, self._armors)
        )
        if bonus:
            lines.append(f"While worn: {bonus}")
        variant = self.selected_variant
        if variant:
            lines.append(f"{variant['name']} ({variant['generation']}, {variant.get('price', 0)} cR): "
                         f"{variant.get('description', '')}")
        elif not self._variants:
            lines.append("This suit does not take Mjolnir variants.")
        self.details.setText("\n\n".join(line for line in lines if line))

    @property
    def selected_armor(self):
        return self.armor_combo.currentData()

    @property
    def selected_variant(self):
        index = self.variant_combo.currentIndex()
        return self._variants[index - 1] if 0 < index <= len(self._variants) else None
