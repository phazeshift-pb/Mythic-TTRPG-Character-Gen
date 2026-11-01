# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Experience tier and creation point allocation.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QPushButton

from src.models.character import CHAR_CODES


class CreationPointsMixin:
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
        all_points_allocated = total_points > 0 and spent == total_points
        self.next_button.setEnabled(all_points_allocated)
        self.character_setup_home.set_all_stat_points_allocated(
            all_points_allocated
        )
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
        luck_available = 0

        for tier in tiers:
            xp_range = tier.get("xp", "")
            if "+" in xp_range:
                lower_bound = int(xp_range.replace("+", "").replace(",", ""))
                if experience >= lower_bound:
                    tier_number = tier["tier"]
                    luck_available = tier.get("luck", 0)
            else:
                bounds = xp_range.replace("–", "-").replace(",", "").split("-")
                if len(bounds) == 2 and int(bounds[0]) <= experience <= int(bounds[1]):
                    tier_number = tier["tier"]
                    luck_available = tier.get("luck", 0)

        self._starting_luck = luck_available
        self.experience_tier_label.setText(f"Tier: {tier_number}")
        self.update_outlier_selection()
        self.refresh_selection_options()
