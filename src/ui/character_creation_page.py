from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class CharacterCreationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        header.addWidget(self.back_button)
        header.addWidget(QLabel("Creation points:"))
        self.creation_points_combo = QComboBox()
        header.addWidget(self.creation_points_combo)
        self.reset_creation_button = QPushButton("Reset Points")
        header.addWidget(self.reset_creation_button)
        self.creation_points_remaining_label = QLabel("Points remaining: 0")
        header.addWidget(self.creation_points_remaining_label)
        self.specialization_button = QPushButton("Specialization Packs")
        header.addWidget(self.specialization_button)
        self.equipment_button = QPushButton("Equipment Pack")
        header.addWidget(self.equipment_button)
        layout.addLayout(header)

        self.characteristic_grid = QGridLayout()
        self.characteristic_value_labels = {}
        self.characteristic_buttons = {}
        layout.addLayout(self.characteristic_grid)

        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)
