from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class OutlierPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Outliers")
        title.setStyleSheet(
            "font-size: 24px; font-weight: bold; "
            "padding: 10px; border-bottom: 2px solid #526b28;"
        )
        header.addWidget(title)
        header.addStretch()
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
        self.done_button = QPushButton("Next: Specialization Packs")
        self.home_button = QPushButton("Home")
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.done_button)
        layout.addLayout(navigation)
