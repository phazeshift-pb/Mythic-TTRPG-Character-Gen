# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Outlier selection.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from PySide6.QtWidgets import QInputDialog, QLabel, QMessageBox

from src.models.character import CHAR_CODES, MYTHIC_CHAR_CODES
from src.ui import theme


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

    def _handle_outlier_selection(self, button, outlier, checked):
        outlier_name = outlier.get("name")
        if checked and outlier_name in {"Aptitude", "Forte"}:
            if not hasattr(self, "generated_character"):
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            if outlier_name == "Aptitude":
                characteristic_document = (
                    self.game_data.get("characteristics", "characteristics") or {}
                )
                characteristics = characteristic_document.get(
                    "characteristics", []
                )
                options = [
                    (item["name"], item["id"].upper())
                    for item in characteristics
                    if isinstance(item.get("id"), str)
                    and item["id"].upper() in CHAR_CODES
                    and item.get("name")
                ]
                prompt = "Choose a characteristic to increase by +5:"
            else:
                mythic_names = {
                    "STR": "Strength",
                    "TOU": "Toughness",
                    "AGI": "Agility",
                }
                options = [
                    (mythic_names[code], code)
                    for code in MYTHIC_CHAR_CODES
                ]
                prompt = "Choose a Mythic Characteristic to increase by +1:"

            if not options:
                QMessageBox.warning(
                    self,
                    f"{outlier_name} Selection Unavailable",
                    "No eligible characteristics are available to choose.",
                )
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            previous_choice = self._outlier_characteristics.get(outlier_name)
            current_index = next(
                (
                    index
                    for index, (_, code) in enumerate(options)
                    if code == previous_choice
                ),
                0,
            )
            labels = [label for label, _ in options]
            label, accepted = QInputDialog.getItem(
                self,
                f"{outlier_name} Selection",
                prompt,
                labels,
                current_index,
                False,
            )
            if not accepted:
                button.blockSignals(True)
                button.setChecked(False)
                button.blockSignals(False)
                self.update_outlier_selection()
                return

            selected_code = next(
                code for option_label, code in options if option_label == label
            )
            self._outlier_characteristics[outlier_name] = selected_code
        self.update_outlier_selection()

    def update_outlier_selection(self):
        selected_count = sum(tile.isChecked() for tile, _, _ in self.outlier_tiles)
        luck_cost = sum(cost for tile, _, cost in self.outlier_tiles if tile.isChecked())
        luck_total = self._starting_luck - luck_cost
        self.outlier_page.available_luck_label.setText(
            f"Luck available: {self._starting_luck} / Total: {luck_total}"
        )
        for select_button, _, cost in self.outlier_tiles:
            select_button.setEnabled(select_button.isChecked() or cost <= luck_total)
        self.outlier_done_button.setText(
            f"Next: Specialization Packs ({selected_count}; Burn {luck_cost} Luck)"
        )

    def finish_outlier_selection(self):
        if hasattr(self, "generated_character"):
            self.generated_character.outliers = []
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
                if tile.isChecked():
                    self.generated_character.apply_outlier(
                        outlier,
                        luck_cost,
                        characteristic=self._outlier_characteristics.get(
                            outlier.get("name")
                        ),
                    )
        self.open_specialization_page()
