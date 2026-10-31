from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)
from src.ui import theme


class VersionAndExpansionsPage(QWidget):
    mode_changed = Signal(str)

    OPTIONS = (
        ("Core", "Create a character using the core rules."),
        ("Light & Sky", "Create a character using the Light & Sky expansion."),
    )
    TILE_COLUMNS = 3

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        title = QLabel("Version and Expansions")
        title.setStyleSheet(
            theme.PAGE_TITLE
        )
        layout.addWidget(title)

        self._selected_mode = None
        self.mode_tiles = {}
        self.mode_button_group = QButtonGroup(self)
        self.mode_button_group.setExclusive(True)

        tiles_layout = QGridLayout()
        tiles_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        tiles_layout.setHorizontalSpacing(18)
        tiles_layout.setVerticalSpacing(18)
        for index, (mode, description) in enumerate(self.OPTIONS):
            display_mode = mode.replace("&", "&&")
            display_description = description.replace("&", "&&")
            tile = QPushButton(f"{display_mode}\n\n{display_description}")
            tile.setCheckable(True)
            tile.setMinimumSize(220, 140)
            tile.setStyleSheet(
                "QPushButton {"
                " text-align: left;"
                " background-color: #242424;"
                " color: #f2f0e6;"
                " border: 2px solid #526b28;"
                " border-radius: 8px;"
                " padding: 14px;"
                " font-size: 15px;"
                "}"
                "QPushButton:hover { border-color: #f7d36b; }"
                "QPushButton:checked {"
                " background-color: #35451d;"
                " border: 3px solid #f7d36b;"
                "}"
            )
            tile.toggled.connect(
                lambda checked, selected_mode=mode: self._select_mode(
                    selected_mode, checked
                )
            )
            self.mode_button_group.addButton(tile)
            self.mode_tiles[mode] = tile
            tiles_layout.addWidget(
                tile, index // self.TILE_COLUMNS, index % self.TILE_COLUMNS
            )

        layout.addLayout(tiles_layout)
        layout.addStretch(1)

        navigation = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.home_button = QPushButton("Home")
        self.continue_button = QPushButton("Continue to Initial Setup")
        self.continue_button.setEnabled(False)
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.continue_button)
        layout.addLayout(navigation)

    @property
    def selected_mode(self):
        return self._selected_mode

    def _select_mode(self, mode, checked):
        if checked and mode != self._selected_mode:
            self._selected_mode = mode
            self.continue_button.setEnabled(True)
            self.mode_changed.emit(mode)
