from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class SkillTestDialog(QDialog):
    def __init__(
        self,
        skill_name,
        characteristic_options,
        training_modifier,
        difficulty_options,
        parent=None,
    ):
        super().__init__(parent)
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

    def _update_total(self, index=None):
        characteristic = self.characteristic_selector.currentData()
        difficulty = self.difficulty_selector.currentData()
        if characteristic is None or difficulty is None:
            self.total_label.setText("Total: Not available")
            return

        code, characteristic_value = characteristic
        total = characteristic_value + self._training_modifier + difficulty
        self.total_label.setText(
            f"Total: {code} ({characteristic_value}) "
            f"{self._format_modifier(self._training_modifier)} skill "
            f"{self._format_modifier(difficulty)} difficulty = {total}"
        )
