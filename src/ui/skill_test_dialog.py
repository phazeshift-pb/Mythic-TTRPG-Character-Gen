import random

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from src.models import dice
from src.ui import theme
from src.ui.attack_roll_dialog import outcome_color


class SkillTestDialog(QDialog):
    def __init__(
        self,
        skill_name,
        characteristic_options,
        training_modifier,
        difficulty_options,
        parent=None,
        rng=None,
    ):
        super().__init__(parent)
        self.rng = rng or random.Random()
        self.last_result = None
        self.setWindowTitle(f"{skill_name} Test")
        self.setMinimumWidth(360)
        self._training_modifier = training_modifier

        layout = QVBoxLayout(self)
        form = QFormLayout()

        self.characteristic_selector = QComboBox(self)
        for name, code, value in characteristic_options:
            self.characteristic_selector.addItem(name, (code, value))
        form.addRow("Characteristic:", self.characteristic_selector)

        self.skill_bonus_label = QLabel(
            self._format_modifier(training_modifier)
        )
        form.addRow("Skill training:", self.skill_bonus_label)

        self.difficulty_selector = QComboBox(self)
        for name, modifier in difficulty_options:
            self.difficulty_selector.addItem(
                f"{name} ({self._format_modifier(modifier)})", modifier
            )
        challenging_index = self.difficulty_selector.findText(
            "Challenging (+0)"
        )
        if challenging_index >= 0:
            self.difficulty_selector.setCurrentIndex(challenging_index)
        form.addRow("Difficulty:", self.difficulty_selector)

        layout.addLayout(form)
        self.total_label = QLabel()
        self.total_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(self.total_label)

        self.roll_button = QPushButton("Roll")
        self.roll_button.setToolTip("Roll a D100 against the total.")
        self.roll_button.clicked.connect(self.roll)
        layout.addWidget(self.roll_button)
        self.roll_result_label = QLabel("")
        self.roll_result_label.setTextFormat(Qt.TextFormat.RichText)
        self.roll_result_label.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(self.roll_result_label)
        self.roll_note_label = QLabel("")
        self.roll_note_label.setWordWrap(True)
        self.roll_note_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(self.roll_note_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)

        self.characteristic_selector.currentIndexChanged.connect(
            self._update_total
        )
        self.difficulty_selector.currentIndexChanged.connect(self._update_total)
        self._update_total()

    @staticmethod
    def _format_modifier(value):
        return f"{value:+d}"

    def current_total(self):
        """(total, characteristic value) for the current choices, or None."""
        characteristic = self.characteristic_selector.currentData()
        difficulty = self.difficulty_selector.currentData()
        if characteristic is None or difficulty is None:
            return None
        _, characteristic_value = characteristic
        return characteristic_value + self._training_modifier + difficulty, characteristic_value

    def roll(self):
        current = self.current_total()
        if current is None:
            return None
        total, characteristic_value = current
        result = dice.resolve_test(dice.roll_d100(self.rng), total, characteristic_value)
        self.last_result = result
        self.roll_button.setText("Roll Again")
        self.roll_result_label.setText(
            f"Rolled <b>{result.roll:02d}</b> vs {total}: "
            f"<span style='color:{outcome_color(result)}'>{result.outcome}</span>, "
            f"{result.degrees_text}"
        )
        notes = {
            "success": "Critical Success (natural 01): automatically succeeds, with at least "
                       "as many Degrees of Success as the Characteristic Modifier.",
            "failure": "Critical Failure (natural 100): automatically fails; the GM picks a fitting consequence.",
        }
        self.roll_note_label.setText(notes.get(result.critical, result.note))
        return result

    def _update_total(self, index=None):
        current = self.current_total()
        if current is None:
            self.total_label.setText("Total: Not available")
            return

        code, characteristic_value = self.characteristic_selector.currentData()
        total = current[0]
        difficulty = self.difficulty_selector.currentData()
        self.total_label.setText(
            f"Total: {code} ({characteristic_value}) "
            f"{self._format_modifier(self._training_modifier)} skill "
            f"{self._format_modifier(difficulty)} difficulty = {total}"
        )
