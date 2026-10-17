from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class EquipmentPage(QWidget):
    light_category_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.title = QLabel("EQUIPMENT PACK")
        header.addWidget(self.title)
        header.addStretch()
        layout.addLayout(header)

        content_layout = QHBoxLayout()
        self.category_panel = QWidget()
        self.category_panel.setFixedWidth(210)
        self.category_layout = QVBoxLayout(self.category_panel)
        self.category_layout.setContentsMargins(0, 0, 12, 0)
        self.category_button_group = QButtonGroup(self)
        self.category_button_group.setExclusive(True)
        self.category_buttons = {}
        self._add_light_category("aspects", "Light Aspects")
        self._add_light_category("powers", "Light Abilities / Grenades")
        self.category_panel.hide()
        content_layout.addWidget(self.category_panel)

        self.options_panel = QWidget()
        options_layout = QVBoxLayout(self.options_panel)
        options_layout.setContentsMargins(0, 0, 0, 0)
        self.experience_remaining_label = QLabel("XP remaining: 0 / 0")
        self.experience_remaining_label.setStyleSheet(
            "font-size: 16px; font-weight: bold; padding: 4px;"
        )
        self.experience_remaining_label.hide()
        options_layout.addWidget(self.experience_remaining_label)
        self.options_title = QLabel()
        self.options_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        self.options_title.hide()
        options_layout.addWidget(self.options_title)
        self.options_description = QLabel()
        self.options_description.setWordWrap(True)
        self.options_description.hide()
        options_layout.addWidget(self.options_description)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.content = QWidget()
        self.content.setStyleSheet("background-color: #242424;")
        self.grid = QGridLayout(self.content)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.grid.setSpacing(14)
        self.scroll_area.setWidget(self.content)
        options_layout.addWidget(self.scroll_area)
        content_layout.addWidget(self.options_panel, 1)
        for column in range(3):
            self.grid.setColumnStretch(column, 1)
        layout.addLayout(content_layout, 1)
        self.tiles = []
        self.light_aspect_tiles = []
        self.light_ability_tiles = []

        navigation = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.home_button = QPushButton("Home")
        self.done_button = QPushButton("Done")
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.done_button)
        layout.addLayout(navigation)

    def _add_light_category(self, key, label):
        button = QPushButton(label, self.category_panel)
        button.setCheckable(True)
        button.setMinimumHeight(48)
        button.setStyleSheet(
            "QPushButton {"
            " text-align: left;"
            " background-color: #242424;"
            " color: #f2f0e6;"
            " border: 2px solid #526b28;"
            " border-radius: 6px;"
            " padding: 8px;"
            " font-weight: bold;"
            "}"
            "QPushButton:hover { border-color: #f7d36b; }"
            "QPushButton:checked {"
            " background-color: #35451d;"
            " border: 3px solid #f7d36b;"
            "}"
        )
        button.clicked.connect(
            lambda checked=False, category=key: self._on_light_category_clicked(
                category, checked
            )
        )
        self.category_button_group.addButton(button)
        self.category_buttons[key] = button
        self.category_layout.addWidget(button)

    def _on_light_category_clicked(self, category, checked):
        if checked:
            self.light_category_selected.emit(category)

    def set_light_mode(self, enabled):
        self.category_panel.setVisible(enabled)
        self.experience_remaining_label.setVisible(enabled)
        self.options_title.setVisible(enabled)
        self.options_description.setVisible(enabled)

    def select_light_category(self, category):
        button = self.category_buttons.get(category)
        if button is not None:
            button.setChecked(True)
