from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class SpecializationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Specialization Packs")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; "
            "padding: 10px; border-bottom: 2px solid #526b28;"
        )
        header.addWidget(title)
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

        navigation = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.home_button = QPushButton("Home")
        self.next_button = QPushButton("Next: Equipment Packs")
        self.done_button = self.next_button
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.next_button)
        layout.addLayout(navigation)
