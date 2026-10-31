from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from src.ui import theme


class CharacterSetupHome(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        header.addStretch(1)
        self.debug_button = QPushButton("Debug")
        header.addWidget(self.debug_button)
        layout.addLayout(header)

        layout.addStretch(1)

        title = QLabel("Character Creator")
        title.setStyleSheet("font-size: 26px; font-weight: bold;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        experience_row = QHBoxLayout()
        experience_row.addWidget(QLabel("Starting XP:"))
        self.experience_input = QSpinBox()
        self.experience_input.setRange(0, 10_000_000)
        self.experience_input.setValue(0)
        self.experience_tier_label = QLabel("Tier: 0")
        experience_row.addWidget(self.experience_input)
        experience_row.addWidget(self.experience_tier_label)
        layout.addLayout(experience_row)

        self.version_and_expansions_button = QPushButton("Version and Expansions")
        self.initial_setup_button = QPushButton("Initial Character Setup")
        self.stat_point_allocation_button = QPushButton("Stat Point Allocation")
        self.outliers_button = QPushButton("Outliers")
        self.specialization_packs_button = QPushButton("Specialization Packs")
        self.equipment_or_light_powers_button = QPushButton("Equipment")
        for button in (
            self.version_and_expansions_button,
            self.initial_setup_button,
            self.stat_point_allocation_button,
            self.outliers_button,
            self.specialization_packs_button,
            self.equipment_or_light_powers_button,
        ):
            button.setMinimumSize(280, 90)
            button.setStyleSheet(
                theme.HOME_MENU_BUTTON
            )
            layout.addWidget(button)
        layout.addStretch(1)

        self.finish_character_button = QPushButton(
            "Finish and Name Your Character"
        )
        self.finish_character_button.setMinimumHeight(56)
        self.finish_character_button.setStyleSheet(
            theme.HOME_MENU_BUTTON
        )
        layout.addWidget(self.finish_character_button)

        self.home_buttons = (
            self.debug_button,
            self.version_and_expansions_button,
            self.initial_setup_button,
            self.stat_point_allocation_button,
            self.outliers_button,
            self.specialization_packs_button,
            self.equipment_or_light_powers_button,
        )
        self._has_version_selection = False
        self._initial_setup_complete = False
        self._all_stat_points_allocated = False
        self._has_specialization_selection = False
        self._character_ready_to_export = False
        self.experience_input.valueChanged.connect(
            self._update_button_availability
        )
        self._update_button_availability()

    def set_version_selected(self, selected):
        self._has_version_selection = selected
        self._update_button_availability()

    def set_initial_setup_complete(self, complete):
        self._initial_setup_complete = complete
        self._update_button_availability()

    def set_all_stat_points_allocated(self, allocated):
        self._all_stat_points_allocated = allocated
        self._update_button_availability()

    def set_specialization_selected(self, selected):
        self._has_specialization_selection = selected
        self._update_button_availability()

    def set_character_ready_to_export(self, ready):
        self._character_ready_to_export = ready
        self._update_button_availability()

    def _update_button_availability(self):
        has_starting_xp = self.experience_input.value() > 0
        for button in self.home_buttons:
            if button is self.version_and_expansions_button:
                button.setEnabled(has_starting_xp)
            elif button is self.initial_setup_button:
                button.setEnabled(
                    has_starting_xp and self._has_version_selection
                )
            elif button is self.stat_point_allocation_button:
                button.setEnabled(
                    has_starting_xp
                    and self._has_version_selection
                    and self._initial_setup_complete
                )
            elif button in (
                self.outliers_button,
                self.specialization_packs_button,
            ):
                button.setEnabled(
                    has_starting_xp
                    and self._has_version_selection
                    and self._initial_setup_complete
                    and self._all_stat_points_allocated
                )
            elif button is self.equipment_or_light_powers_button:
                button.setEnabled(
                    has_starting_xp
                    and self._has_version_selection
                    and self._initial_setup_complete
                    and self._all_stat_points_allocated
                    and self._has_specialization_selection
                )
            else:
                button.setEnabled(False)
        self.finish_character_button.setEnabled(
            has_starting_xp
            and self._has_version_selection
            and self._initial_setup_complete
            and self._all_stat_points_allocated
            and self._has_specialization_selection
            and self._character_ready_to_export
        )
