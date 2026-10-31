from PySide6.QtCore import QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import (
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QToolTip,
    QVBoxLayout,
    QWidget,
)
from src.ui import theme


class DelayedTooltipLabel(QLabel):
    def __init__(self, text, description, parent=None):
        super().__init__(text, parent)
        self._description = description
        self._tooltip_timer = QTimer(self)
        self._tooltip_timer.setSingleShot(True)
        self._tooltip_timer.setInterval(1000)
        self._tooltip_timer.timeout.connect(self._show_description)
        self.setStyleSheet(
            "QLabel { color: #ffffff; padding: 3px; }"
            "QLabel:hover { color: #90ee90; }"
        )

    def enterEvent(self, event):
        if self._description:
            self._tooltip_timer.start()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self._tooltip_timer.stop()
        QToolTip.hideText()
        super().leaveEvent(event)

    def _show_description(self):
        if self.underMouse():
            QToolTip.showText(QCursor.pos(), self._description, self)


class SpecializationPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Specialization Packs")
        title.setStyleSheet(
            theme.PAGE_TITLE
        )
        header.addWidget(title)
        layout.addLayout(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setStyleSheet(theme.PANEL_BACKGROUND)
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
