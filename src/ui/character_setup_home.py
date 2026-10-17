from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CharacterSetupHome(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addStretch(1)
        self.debug_button = QPushButton("Debug")
        header.addWidget(self.debug_button)
        layout.addLayout(header)

        layout.addStretch(1)

        title = QLabel("Character Creator")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        experience_row = QHBoxLayout()
        experience_row.addWidget(QLabel("Starting XP:"))
        self.experience_input = QSpinBox()
        self.experience_input.setRange(0, 10_000_000)
        self.experience_input.setValue(0)
        self.experience_tier_label = QLabel("Tier: 0")
        experience_row.addWidget(self.experience_input)
        experience_row.addWidget(self.experience_tier_label)
        layout.addLayout(experience_row)

        self.version_and_expansions_button = QPushButton("Version and Expansions")
        self.initial_setup_button = QPushButton("Initial Character Setup")
        self.stat_point_allocation_button = QPushButton("Stat Point Allocation")
        self.outliers_button = QPushButton("Outliers")
        self.specialization_packs_button = QPushButton("Specialization Packs")
        self.equipment_or_light_powers_button = QPushButton("Equipment")
        for button in (
            self.version_and_expansions_button,
            self.initial_setup_button,
            self.stat_point_allocation_button,
            self.outliers_button,
            self.specialization_packs_button,
            self.equipment_or_light_powers_button,
        ):
            button.setMinimumSize(280, 90)
            button.setStyleSheet(
                "QPushButton { font-size: 18px; font-weight: bold; padding: 12px; }"
                "QPushButton:hover { border: 2px solid #f7d36b; }"
            )
            layout.addWidget(button)
        layout.addStretch(1)
