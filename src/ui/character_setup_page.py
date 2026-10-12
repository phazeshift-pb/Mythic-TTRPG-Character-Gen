from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class CharacterSetupPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selection_layout = QVBoxLayout(self)

        experience_row = QHBoxLayout()
        experience_row.addWidget(QLabel("Starting XP:"))
        self.experience_input = QSpinBox()
        self.experience_input.setRange(0, 10_000_000)
        self.experience_input.setValue(0)
        self.experience_tier_label = QLabel("Tier: 0")
        experience_row.addWidget(self.experience_input)
        experience_row.addWidget(self.experience_tier_label)
        self.selection_layout.addLayout(experience_row)

        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Mode:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Core", "Light & Sky"])
        mode_row.addWidget(self.mode_combo)
        self.selection_layout.addLayout(mode_row)

        soldier_row = QHBoxLayout()
        self.soldier_label = QLabel("Soldier Type:")
        self.soldier_combo = QComboBox()
        soldier_row.addWidget(self.soldier_label)
        soldier_row.addWidget(self.soldier_combo)
        self.selection_layout.addLayout(soldier_row)
        self.core_soldier_row = soldier_row

        upbringing_row = QHBoxLayout()
        self.upbringing_label = QLabel("Upbringing:")
        self.upbringing_combo = QComboBox()
        upbringing_row.addWidget(self.upbringing_label)
        upbringing_row.addWidget(self.upbringing_combo)
        self.selection_layout.addLayout(upbringing_row)

        environment_row = QHBoxLayout()
        self.environment_label = QLabel("Environment:")
        self.environment_combo = QComboBox()
        environment_row.addWidget(self.environment_label)
        environment_row.addWidget(self.environment_combo)
        self.selection_layout.addLayout(environment_row)

        self.lifestyle_label = QLabel("Lifestyle 1:")
        self.lifestyle_two_label = QLabel("Lifestyle 2:")
        self.lifestyle_three_label = QLabel("Lifestyle 3:")
        self.lifestyle_combo = QComboBox()
        self.lifestyle_two_combo = QComboBox()
        self.lifestyle_three_combo = QComboBox()
        self.lifestyle_combos = (
            self.lifestyle_combo,
            self.lifestyle_two_combo,
            self.lifestyle_three_combo,
        )
        for label, combo in zip(
            (
                self.lifestyle_label,
                self.lifestyle_two_label,
                self.lifestyle_three_label,
            ),
            self.lifestyle_combos,
        ):
            row = QHBoxLayout()
            row.addWidget(label)
            row.addWidget(combo)
            self.selection_layout.addLayout(row)

        self.core_background_widgets = (
            self.upbringing_label,
            self.upbringing_combo,
            self.environment_label,
            self.environment_combo,
            self.lifestyle_label,
            self.lifestyle_two_label,
            self.lifestyle_three_label,
            *self.lifestyle_combos,
        )

        human_row = QHBoxLayout()
        self.human_label = QLabel("Human Soldier Type:")
        self.human_combo = QComboBox()
        human_row.addWidget(self.human_label)
        human_row.addWidget(self.human_combo)
        self.selection_layout.addLayout(human_row)

        guardian_row = QHBoxLayout()
        self.guardian_label = QLabel("Guardian Class Soldier Type:")
        self.guardian_combo = QComboBox()
        guardian_row.addWidget(self.guardian_label)
        guardian_row.addWidget(self.guardian_combo)
        self.selection_layout.addLayout(guardian_row)

        subclass_row = QHBoxLayout()
        self.subclass_label = QLabel("Subclass:")
        self.subclass_combo = QComboBox()
        subclass_row.addWidget(self.subclass_label)
        subclass_row.addWidget(self.subclass_combo)
        self.selection_layout.addLayout(subclass_row)

        connection_row = QHBoxLayout()
        self.connection_label = QLabel("Connection:")
        self.connection_combo = QComboBox()
        connection_row.addWidget(self.connection_label)
        connection_row.addWidget(self.connection_combo)
        self.selection_layout.addLayout(connection_row)

        self.human_row_widgets = (self.human_label, self.human_combo)
        self.guardian_row_widgets = (self.guardian_label, self.guardian_combo)

        self.generate_button = QPushButton("Generate Character")
        self.selection_layout.addWidget(self.generate_button)
