from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class DebugPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("Character Generator Debug")
        title.setStyleSheet("font-size: 24px; font-weight: bold; padding: 10px;")
        header.addWidget(title)
        header.addStretch(1)
        layout.addLayout(header)

        self.report = QPlainTextEdit()
        self.report.setReadOnly(True)
        self.report.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.report, 1)

        navigation = QHBoxLayout()
        navigation.addStretch(1)
        self.home_button = QPushButton("Back to Home")
        navigation.addWidget(self.home_button)
        layout.addLayout(navigation)

    def set_report(self, text):
        self.report.setPlainText(text)
