# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Outlier selection.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.

Outliers that can be taken more than once (book rules, set in the data):
- Enduring, Robust, Vigorous (``max_times``): a "Times taken" box on the card.
- Aptitude, Forte (``max_times_per_characteristic`` / ``max_times_per_mythic``):
  a dialog to pick a Characteristic for each time taken (up to twice each).
Each take burns the outlier's Luck again.
"""

from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QSpinBox,
    QVBoxLayout,
)

from src.models import outliers as outlier_rules
from src.models.character import CHAR_CODES, MYTHIC_CHAR_CODES
from src.ui import theme

MYTHIC_NAMES = {"STR": "Strength", "TOU": "Toughness", "AGI": "Agility"}


class OutlierPicksDialog(QDialog):
    """Choose how many times Aptitude / Forte goes on each Characteristic."""

    def __init__(self, outlier, options, previous, max_takes, parent=None):
        super().__init__(parent)
        name = outlier.get("name", "Outlier")
        per_choice = outlier_rules.max_per_choice(outlier)
        self.setWindowTitle(f"{name} Selection")
        self.max_takes = max_takes
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(
            f"{outlier.get('effect', '')}\nPick up to {per_choice} per Characteristic. "
            f"Each pick burns Luck (Luck allows {max_takes})."
        ))
        form = QFormLayout()
        self.inputs = {}
        for label, code in options:
            spin = QSpinBox()
            spin.setRange(0, per_choice)
            spin.setValue(min(per_choice, list(previous).count(code)))
            spin.valueChanged.connect(self._update)
            form.addRow(label, spin)
            self.inputs[code] = spin
        layout.addLayout(form)
        self.total_label = QLabel()
        layout.addWidget(self.total_label)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update()

    def picks(self):
        return [code for code, spin in self.inputs.items() for _ in range(spin.value())]

    def _update(self, *_):
        count = len(self.picks())
        self.total_label.setText(f"Picks: {count} / {self.max_takes}")
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            1 <= count <= self.max_takes
        )


class OutliersMixin:
    def _build_outlier_tiles(self):
        while self.outlier_grid.count():
            item = self.outlier_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.outlier_tiles.clear()
        self._outlier_rank_inputs = {}
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
                theme.TILE_TITLE
            )
            self.outlier_grid.addWidget(section_label, row, 0, 1, 3)
            row += 1

            for index, outlier in enumerate(outliers):
                card, select_button = self._create_selection_tile(
                    outlier["name"],
                    outlier["effect"],
                    min_height=125,
                    parent=self.outlier_content,
                )
                if (
                    outlier_rules.needs_choice(outlier) is None
                    and outlier_rules.max_times(outlier) > 1
                ):
                    self._add_outlier_rank_input(card, outlier)
                select_button.toggled.connect(
                    lambda checked, button=select_button, selected_outlier=outlier:
                    self._handle_outlier_selection(
                        button, selected_outlier, checked
                    )
                )
                self.outlier_tiles.append((select_button, outlier, luck_cost))
                self.outlier_grid.addWidget(card, row + index // 3, index % 3)

            row += (len(outliers) + 2) // 3 + 1
        self.update_outlier_selection()

    def _add_outlier_rank_input(self, card, outlier):
        """A "Times taken" box for Enduring / Robust / Vigorous, shown while selected."""
        row = QHBoxLayout()
        label = QLabel("Times taken", card)
        label.setStyleSheet(theme.TILE_TEXT)
        spin = QSpinBox(card)
        spin.setRange(1, outlier_rules.max_times(outlier))
        spin.setToolTip(outlier.get("second_rank_effect", ""))
        spin.valueChanged.connect(lambda _value: self.update_outlier_selection())
        row.addWidget(label)
        row.addWidget(spin)
        row.addStretch(1)
        card.layout().addLayout(row)
        label.hide()
        spin.hide()
        self._outlier_rank_inputs[outlier["name"]] = (label, spin)

    def _reset_outlier_tiles(self):
        """Unselect every outlier and put "Times taken" boxes back to 1."""
        for tile, outlier, _ in self.outlier_tiles:
            tile.blockSignals(True)
            tile.setChecked(False)
            tile.blockSignals(False)
            tile.setText(outlier["name"])
        for label, spin in getattr(self, "_outlier_rank_inputs", {}).values():
            spin.blockSignals(True)
            spin.setValue(1)
            spin.blockSignals(False)
            label.hide()
            spin.hide()

    def _outlier_times(self, outlier, checked=True):
        """How many times a selected outlier is taken (0 when not selected)."""
        if not checked:
            return 0
        name = outlier.get("name")
        if outlier_rules.needs_choice(outlier):
            return len(self._outlier_characteristics.get(name) or [])
        inputs = getattr(self, "_outlier_rank_inputs", {}).get(name)
        return inputs[1].value() if inputs else 1

    def _outlier_luck_spent(self, skip_outlier=None):
        return sum(
            cost * self._outlier_times(outlier, tile.isChecked())
            for tile, outlier, cost in self.outlier_tiles
            if outlier is not skip_outlier
        )

    def _uncheck_outlier(self, button):
        button.blockSignals(True)
        button.setChecked(False)
        button.blockSignals(False)
        self.update_outlier_selection()

    def _handle_outlier_selection(self, button, outlier, checked):
        outlier_name = outlier.get("name")
        kind = outlier_rules.needs_choice(outlier)
        rank_inputs = getattr(self, "_outlier_rank_inputs", {}).get(outlier_name)
        if rank_inputs:
            for widget in rank_inputs:
                widget.setVisible(checked)
            if checked:
                cost = next(c for _, o, c in self.outlier_tiles if o is outlier)
                spare = self._starting_luck - self._outlier_luck_spent(outlier)
                rank_inputs[1].setMaximum(
                    max(1, min(outlier_rules.max_times(outlier), spare // max(1, cost)))
                )
        if not checked:
            self._outlier_characteristics.pop(outlier_name, None)
            button.setText(outlier_name)
            self.update_outlier_selection()
            return

        if kind:
            if not hasattr(self, "generated_character"):
                self._uncheck_outlier(button)
                return
            if kind == "characteristic":
                characteristic_document = (
                    self.game_data.get("characteristics", "characteristics") or {}
                )
                options = [
                    (item["name"], item["id"].upper())
                    for item in characteristic_document.get("characteristics", [])
                    if isinstance(item.get("id"), str)
                    and item["id"].upper() in CHAR_CODES
                    and item.get("name")
                ]
            else:
                options = [(MYTHIC_NAMES[code], code) for code in MYTHIC_CHAR_CODES]
            if not options:
                QMessageBox.warning(
                    self,
                    f"{outlier_name} Selection Unavailable",
                    "No eligible characteristics are available to choose.",
                )
                self._uncheck_outlier(button)
                return

            cost = next(c for _, o, c in self.outlier_tiles if o is outlier)
            spare = self._starting_luck - self._outlier_luck_spent(outlier)
            max_takes = spare // max(1, cost)
            previous = self._outlier_characteristics.get(outlier_name) or []
            if isinstance(previous, str):
                previous = [previous]
            dialog = OutlierPicksDialog(outlier, options, previous, max_takes, self)
            if max_takes < 1 or not dialog.exec():
                self._uncheck_outlier(button)
                return
            picks = dialog.picks()
            self._outlier_characteristics[outlier_name] = picks
            labels = {code: label for label, code in options}
            button.setText(
                f"{outlier_name}: " + ", ".join(labels.get(code, code) for code in picks)
            )
        self.update_outlier_selection()

    def update_outlier_selection(self):
        selected_count = sum(
            self._outlier_times(outlier, tile.isChecked())
            for tile, outlier, _ in self.outlier_tiles
        )
        luck_cost = self._outlier_luck_spent()
        luck_total = self._starting_luck - luck_cost
        self.outlier_page.available_luck_label.setText(
            f"Luck available: {self._starting_luck} / Total: {luck_total}"
        )
        for select_button, outlier, cost in self.outlier_tiles:
            select_button.setEnabled(select_button.isChecked() or cost <= luck_total)
            inputs = getattr(self, "_outlier_rank_inputs", {}).get(outlier.get("name"))
            if inputs and select_button.isChecked():
                spin = inputs[1]
                spare = luck_total + cost * spin.value()
                spin.blockSignals(True)
                spin.setMaximum(
                    max(1, min(outlier_rules.max_times(outlier), spare // max(1, cost)))
                )
                spin.blockSignals(False)
        self.outlier_done_button.setText(
            f"Next: Specialization Packs ({selected_count}; Burn {luck_cost} Luck)"
        )

    def finish_outlier_selection(self):
        if hasattr(self, "generated_character"):
            self.generated_character.clear_outliers(
                {outlier["name"]: outlier for _, outlier, _ in self.outlier_tiles}
            )
            self.generated_character.luck_available = self._starting_luck
            self.generated_character.luck_total = self._starting_luck
            self.generated_character.characteristics = {
                code: self._generated_characteristics[code]
                + self._creation_allocations[code]
                for code in CHAR_CODES
            }
            self.generated_character.mythic_characteristics = (
                self._pre_outlier_mythic_characteristics.copy()
            )
            for tile, outlier, luck_cost in self.outlier_tiles:
                if not tile.isChecked():
                    continue
                if outlier_rules.needs_choice(outlier):
                    picks = self._outlier_characteristics.get(outlier.get("name")) or []
                    for code in [picks] if isinstance(picks, str) else picks:
                        self.generated_character.apply_outlier(
                            outlier, luck_cost, characteristic=code
                        )
                else:
                    for _ in range(self._outlier_times(outlier)):
                        self.generated_character.apply_outlier(outlier, luck_cost)
        self.open_specialization_page()
