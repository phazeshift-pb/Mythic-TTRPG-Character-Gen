from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)
from src.ui import theme


class InitialCharacterSetupPage(QWidget):
    option_selected = Signal(str, str, bool)
    selection_requirements_changed = Signal(bool)

    TILE_COLUMNS = 3
    LIFESTYLE_TILE_COLUMNS = 2

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        title = QLabel("Initial Character Setup")
        title.setStyleSheet(
            theme.PAGE_TITLE
        )
        layout.addWidget(title)

        content_layout = QHBoxLayout()
        self.category_panel = QWidget()
        self.category_panel.setFixedWidth(210)
        self.category_layout = QVBoxLayout(self.category_panel)
        self.category_layout.setContentsMargins(0, 0, 12, 0)
        self.category_buttons = {}
        content_layout.addWidget(self.category_panel)

        self.options_panel = QWidget()
        options_layout = QVBoxLayout(self.options_panel)
        options_layout.setContentsMargins(0, 0, 0, 0)
        self.options_title = QLabel()
        self.options_title.setStyleSheet(theme.SECTION_HEADING)
        options_layout.addWidget(self.options_title)
        self.options_description = QLabel()
        self.options_description.setWordWrap(True)
        options_layout.addWidget(self.options_description)

        self.options_scroll = QScrollArea()
        self.options_scroll.setWidgetResizable(True)
        self.options_content = QWidget()
        self.options_grid = QGridLayout(self.options_content)
        self.options_grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.options_grid.setSpacing(14)
        self.options_scroll.setWidget(self.options_content)
        options_layout.addWidget(self.options_scroll)
        content_layout.addWidget(self.options_panel, 1)
        layout.addLayout(content_layout, 1)

        navigation = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.home_button = QPushButton("Home")
        self.generate_button = QPushButton("Next: Stat Point Allocation")
        navigation.addWidget(self.back_button)
        navigation.addStretch(1)
        navigation.addWidget(self.home_button)
        navigation.addStretch(1)
        navigation.addWidget(self.generate_button)
        layout.addLayout(navigation)

        self.category_button_group = QButtonGroup(self)
        self.category_button_group.setExclusive(True)
        self.option_button_group = None
        self._category_options = {}
        self._required_categories = ()
        self._selected_category = None

        self.selection_state = QWidget(self)
        self.selection_state.hide()

        self.soldier_combo = QComboBox(self.selection_state)
        self.human_combo = QComboBox(self.selection_state)
        self.guardian_combo = QComboBox(self.selection_state)
        self.upbringing_combo = QComboBox(self.selection_state)
        self.environment_combo = QComboBox(self.selection_state)
        self.lifestyle_combos = (
            QComboBox(self.selection_state),
            QComboBox(self.selection_state),
            QComboBox(self.selection_state),
        )
        (
            self.lifestyle_combo,
            self.lifestyle_two_combo,
            self.lifestyle_three_combo,
        ) = self.lifestyle_combos
        self.subclass_combo = QComboBox(self.selection_state)
        self.connection_combo = QComboBox(self.selection_state)

    def set_categories(self, categories):
        self._required_categories = tuple(key for key, _ in categories)
        self._category_options.clear()
        self._update_selection_completion()
        while self.category_layout.count():
            item = self.category_layout.takeAt(0)
            widget = item.widget()
            if widget:
                self.category_button_group.removeButton(widget)
                widget.deleteLater()
        self.category_buttons.clear()

        for key, label in categories:
            button = QPushButton(label, self.category_panel)
            button.setCheckable(True)
            button.setMinimumHeight(48)
            button.setStyleSheet(
                theme.CATEGORY_BUTTON
            )
            button.clicked.connect(
                lambda checked=False, category=key: self.select_category(category)
            )
            self.category_button_group.addButton(button)
            self.category_buttons[key] = button
            self.category_layout.addWidget(button)
        self.category_layout.addStretch(1)

        if self._selected_category not in self.category_buttons:
            self._selected_category = next(iter(self.category_buttons), None)
        if self._selected_category:
            self.category_buttons[self._selected_category].setChecked(True)
            self._render_options()

    def set_category_options(self, category, title, options, selected_values=()):
        self._category_options[category] = (
            title,
            tuple(options),
            tuple(selected_values),
        )
        self._update_selection_completion()
        if category == self._selected_category:
            self._render_options()

    def _update_selection_completion(self):
        complete = bool(self._required_categories) and all(
            category in self._category_options
            and (
                len(self._category_options[category][2]) == 3
                if category == "lifestyles"
                else bool(self._category_options[category][2])
            )
            for category in self._required_categories
        )
        self.generate_button.setEnabled(complete)
        self.selection_requirements_changed.emit(complete)

    def select_category(self, category):
        if category not in self.category_buttons:
            return
        self._selected_category = category
        self.category_buttons[category].setChecked(True)
        self._render_options()

    def _render_options(self):
        while self.options_grid.count():
            item = self.options_grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        if self.option_button_group:
            self.option_button_group.deleteLater()
            self.option_button_group = None

        if self._selected_category not in self._category_options:
            self.options_title.setText("")
            self.options_description.setText("")
            return

        title, options, selected_values = self._category_options[
            self._selected_category
        ]
        self.options_title.setText(title)
        is_lifestyle = self._selected_category == "lifestyles"
        self.options_description.setText(
            "Select exactly 3 lifestyles. You may select the same lifestyle more than once."
            if is_lifestyle
            else "Select one option."
        )

        if not is_lifestyle:
            self.option_button_group = QButtonGroup(self)
            self.option_button_group.setExclusive(True)

        selected_counts = {}
        for value in selected_values:
            selected_counts[value] = selected_counts.get(value, 0) + 1

        for index, (label, value, details) in enumerate(options):
            if is_lifestyle:
                self._add_lifestyle_tile(
                    index, label, value, details, selected_counts.get(value, 0)
                )
                continue

            card = QFrame(self.options_content)
            card.setStyleSheet(
                theme.TILE_FRAME
            )
            card_layout = QVBoxLayout(card)
            tile = QPushButton(label, card)
            tile.setCheckable(True)
            tile.setMinimumSize(260, 72)
            tile.setStyleSheet(
                theme.SELECT_BUTTON
            )
            tile.setChecked(value in selected_values)
            if self.option_button_group:
                self.option_button_group.addButton(tile)
            tile.toggled.connect(
                lambda checked, option_value=value, option_category=self._selected_category:
                self.option_selected.emit(option_category, option_value, checked)
            )
            card_layout.addWidget(tile)
            details_label = QLabel(details, card)
            details_label.setWordWrap(True)
            details_label.setStyleSheet(
                theme.TILE_TEXT
            )
            card_layout.addWidget(details_label)
            self.options_grid.addWidget(
                card, index // self.TILE_COLUMNS, index % self.TILE_COLUMNS
            )

        if not options:
            empty_label = QLabel("No options are currently available.")
            self.options_grid.addWidget(empty_label, 0, 0)

    def _add_lifestyle_tile(self, index, label, value, details, selected_count):
        card = QFrame(self.options_content)
        card.setMinimumSize(300, 250)
        card.setStyleSheet(
            theme.TILE_FRAME
        )
        card_layout = QVBoxLayout(card)
        add_button = QPushButton(label, card)
        add_button.setMinimumSize(260, 72)
        add_button.setStyleSheet(
            "QPushButton {"
            " text-align: left;"
            " background-color: #526b28;"
            " color: #ffffff;"
            " border: 2px solid #788f3e;"
            " border-radius: 6px;"
            " padding: 14px;"
            " font-size: 16px;"
            " font-weight: bold;"
            "}"
            "QPushButton:hover {"
            " background-color: #788f3e;"
            " border-color: #f7d36b;"
            "}"
            "QPushButton:pressed {"
            " background-color: #35451d;"
            " border-color: #f7d36b;"
            "}"
        )
        add_button.clicked.connect(
            lambda checked=False, option_value=value:
            self._adjust_lifestyle(option_value, True)
        )
        card_layout.addWidget(add_button)

        details_label = QLabel(details, card)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            "color: #d5d2c6; border: none; padding: 4px 8px; font-size: 13px;"
        )
        card_layout.addWidget(details_label)

        selection_row = QHBoxLayout()
        count_label = QLabel(f"Selected: {selected_count} / 3", card)
        count_label.setStyleSheet("color: #f2f0e6; border: none;")
        remove_button = QPushButton("Remove one", card)
        remove_button.setEnabled(selected_count > 0)
        remove_button.setStyleSheet(
            "QPushButton { color: #f2f0e6; border: 1px solid #788f3e; padding: 4px; }"
            "QPushButton:hover { border-color: #f7d36b; }"
        )
        remove_button.clicked.connect(
            lambda checked=False, option_value=value:
            self._adjust_lifestyle(option_value, False)
        )
        selection_row.addWidget(count_label)
        selection_row.addWidget(remove_button)
        card_layout.addLayout(selection_row)
        self.options_grid.addWidget(
            card,
            index // self.LIFESTYLE_TILE_COLUMNS,
            index % self.LIFESTYLE_TILE_COLUMNS,
        )

    def _adjust_lifestyle(self, value, add):
        selected_values = self._category_options.get("lifestyles", ("", (), ()))[2]
        if add and len(selected_values) >= 3:
            return
        if not add and value not in selected_values:
            return
        self.option_selected.emit("lifestyles", value, add)
