from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LandingPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(48, 40, 48, 40)
        layout.addStretch(1)

        title_card = QFrame()
        title_card.setObjectName("titleCard")
        title_card.setFrameShape(QFrame.Shape.StyledPanel)
        title_card_layout = QVBoxLayout(title_card)
        title_label = QLabel("Mythic TTRPG Character Manager")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("font-size: 28px; font-weight: bold;")
        title_card_layout.addWidget(title_label)
        layout.addWidget(title_card)

        layout.addSpacing(32)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(24)
        self.create_character_button = QPushButton("Create New Character")
        self.create_character_button.setMinimumSize(280, 110)
        self.create_character_button.setStyleSheet(
            "QPushButton {"
            " background-color: #526b28;"
            " color: #ffffff;"
            " border: 2px solid #788f3e;"
            " border-radius: 8px;"
            " font-size: 20px;"
            " font-weight: bold;"
            " padding: 16px;"
            "}"
            "QPushButton:hover {"
            " background-color: #788f3e;"
            " border-color: #f7d36b;"
            "}"
        )
        self.load_character_button = QPushButton("Load Character")
        self.load_character_button.setMinimumSize(280, 110)
        self.load_character_button.setStyleSheet(
            self.create_character_button.styleSheet()
        )
        buttons_layout.addStretch(1)
        buttons_layout.addWidget(self.create_character_button)
        buttons_layout.addWidget(self.load_character_button)
        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)
        layout.addStretch(1)
