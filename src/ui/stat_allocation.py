from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class StatAllocationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Stat Point Allocation")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; "
            "padding: 10px; border-bottom: 2px solid #526b28;"
        )
        layout.addWidget(title)
        layout.addStretch(1)

        controls = QHBoxLayout()
        controls.addStretch(1)
        controls.addWidget(QLabel("Creation points:"))
        self.creation_points_combo = QComboBox()
        self.creation_points_combo.setMinimumWidth(180)
        controls.addWidget(self.creation_points_combo)
        self.reset_creation_button = QPushButton("Reset Points")
        controls.addWidget(self.reset_creation_button)
        self.creation_points_remaining_label = QLabel("Points remaining: 0")
        controls.addWidget(self.creation_points_remaining_label)
        controls.addStretch(1)
        layout.addLayout(controls)

        table_container = QHBoxLayout()
        table_container.addStretch(1)
        table = QWidget()
        table.setMinimumWidth(600)
        self.characteristic_grid = QGridLayout(table)
        self.characteristic_grid.setHorizontalSpacing(24)
        self.characteristic_grid.setVerticalSpacing(12)
        self.characteristic_grid.setColumnStretch(0, 2)
        for column in range(1, 4):
            self.characteristic_grid.setColumnStretch(column, 1)
        table_container.addWidget(table)
        table_container.addStretch(1)
        layout.addLayout(table_container)

        layout.addStretch(1)

        navigation = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.home_button = QPushButton("Home")
        self.next_button = QPushButton("Next: Specialization Packs")
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.next_button)
        layout.addLayout(navigation)

        self.characteristic_value_labels = {}
        self.characteristic_buttons = {}
