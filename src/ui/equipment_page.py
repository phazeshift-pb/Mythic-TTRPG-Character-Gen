from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class EquipmentPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.title = QLabel("EQUIPMENT PACK")
        header.addWidget(self.title)
        header.addStretch()
        self.back_button = QPushButton("Back")
        self.done_button = QPushButton("Done")
        header.addWidget(self.back_button)
        header.addWidget(self.done_button)
        layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #242424;")
        self.grid = QGridLayout(self.content)
        self.grid.setSpacing(18)
        for column in range(3):
            self.grid.setColumnStretch(column, 1)
        self.scroll_area.setWidget(self.content)
        layout.addWidget(self.scroll_area)
        self.tiles = []
        self.light_aspect_tiles = []
        self.light_ability_tiles = []

        navigation = QHBoxLayout()
        navigation.addStretch(1)
        self.home_button = QPushButton("Home")
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        layout.addLayout(navigation)
