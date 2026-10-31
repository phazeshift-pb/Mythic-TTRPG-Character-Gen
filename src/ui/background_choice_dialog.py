from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QVBoxLayout,
)


class BackgroundChoiceDialog(QDialog):
    """Pick one option from each either/or group of an upbringing or environment."""

    SECTION_LABELS = {"bonuses": "Bonus", "penalties": "Penalty"}

    def __init__(self, title, groups, selected=(), parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Choose {title} Options")
        self.setMinimumWidth(380)

        layout = QVBoxLayout(self)
        intro = QLabel(f"{title} lets you choose. Pick one option for each line.")
        intro.setWordWrap(True)
        layout.addWidget(intro)

        form = QFormLayout()
        self.combos = []
        selected = list(selected or [])
        for index, group in enumerate(groups):
            combo = QComboBox(self)
            combo.addItems(group["labels"])
            previous = selected[index] if index < len(selected) else None
            if previous in group["labels"]:
                combo.setCurrentIndex(group["labels"].index(previous))
            form.addRow(self.SECTION_LABELS.get(group["section"], "Choice"), combo)
            self.combos.append(combo)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    @property
    def selected_choices(self):
        return [combo.currentText() for combo in self.combos]
