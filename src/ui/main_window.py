"""Character creator main window.

MainWindow owns the page stack and the widgets; behaviour for each part of
creation lives in a mixin under src/ui/creator/.
"""

import sys

from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from src.generator.character_generator import CharacterGenerator
from src.models.character import CHAR_CODES
from src.ui.character_setup_home import CharacterSetupHome
from src.ui.debug_page import DebugPage
from src.ui.equipment_page import EquipmentPage
from src.ui.initial_character_setup import InitialCharacterSetupPage
from src.ui.interactive_character_sheet import InteractiveCharacterSheet
from src.ui.landing_page import LandingPage
from src.ui.outlier_page import OutlierPage
from src.ui.specialization_page import SpecializationPage
from src.ui.stat_allocation import StatAllocationPage
from src.ui.version_and_expansions import VersionAndExpansionsPage
from src.ui.xp_shop_page import XpShopPage
from src.ui.creator.character_files import CharacterFilesMixin
from src.ui.creator.debug_report import DebugReportMixin
from src.ui.creator.initial_setup import CreationCancelled, InitialSetupMixin
from src.ui.creator.specialization import SpecializationMixin
from src.ui.creator.outliers import OutliersMixin
from src.ui.creator.equipment import EquipmentMixin
from src.ui.creator.light_powers import LightPowersMixin
from src.ui.creator.creation_points import CreationPointsMixin
from src.ui import theme


class MainWindow(
    CharacterFilesMixin,
    DebugReportMixin,
    InitialSetupMixin,
    SpecializationMixin,
    OutliersMixin,
    EquipmentMixin,
    LightPowersMixin,
    CreationPointsMixin,
    QWidget,
):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mythic TTRPG Character Manager")
        self.resize(900, 650)

        layout = QVBoxLayout(self)
        self.pages = QStackedWidget()

        self.landing_page = LandingPage()
        self.character_setup_home = CharacterSetupHome()
        self.version_and_expansions_page = VersionAndExpansionsPage()
        self.initial_character_setup_page = InitialCharacterSetupPage()
        self.creation_page = StatAllocationPage()
        self.specialization_page = SpecializationPage()
        self.outlier_page = OutlierPage()
        self.equipment_page = EquipmentPage()
        self.debug_page = DebugPage()
        self.character_sheet = InteractiveCharacterSheet()
        self.xp_shop_page = XpShopPage()
        self.page_widgets = (
            self.landing_page,
            self.character_setup_home,
            self.version_and_expansions_page,
            self.initial_character_setup_page,
            self.creation_page,
            self.outlier_page,
            self.specialization_page,
            self.equipment_page,
            self.debug_page,
            self.character_sheet,
            self.xp_shop_page,
        )
        for page in self.page_widgets:
            self.pages.addWidget(page)
        layout.addWidget(self.pages)

        self.create_character_button = self.landing_page.create_character_button
        self.load_character_button = self.landing_page.load_character_button
        self.load_character_button.clicked.connect(self.load_character)
        self.character_sheet.home_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.landing_page)
        )
        self.character_sheet.save_requested.connect(self.save_loaded_character)
        self.character_sheet.spend_xp_button.clicked.connect(self.open_xp_shop)
        self.xp_shop_page.applied.connect(self.apply_xp_shop)
        self.xp_shop_page.cancelled.connect(
            lambda: self.pages.setCurrentWidget(self.character_sheet)
        )
        self.character_setup_home.finish_character_button.clicked.connect(
            self.finish_and_name_character
        )
        self.character_setup_home.discard_button.clicked.connect(
            self.discard_character_creation
        )

        self.experience_input = self.character_setup_home.experience_input
        self.experience_tier_label = self.character_setup_home.experience_tier_label
        self.soldier_combo = self.initial_character_setup_page.soldier_combo
        self.upbringing_combo = self.initial_character_setup_page.upbringing_combo
        self.environment_combo = self.initial_character_setup_page.environment_combo
        self.lifestyle_combos = self.initial_character_setup_page.lifestyle_combos
        self.human_combo = self.initial_character_setup_page.human_combo
        self.guardian_combo = self.initial_character_setup_page.guardian_combo
        self.subclass_combo = self.initial_character_setup_page.subclass_combo
        self.connection_combo = self.initial_character_setup_page.connection_combo
        self.generate_button = self.initial_character_setup_page.generate_button

        self.back_button = self.creation_page.back_button
        self.creation_points_combo = self.creation_page.creation_points_combo
        self.reset_creation_button = self.creation_page.reset_creation_button
        self.creation_points_remaining_label = (
            self.creation_page.creation_points_remaining_label
        )
        self.characteristic_grid = self.creation_page.characteristic_grid
        self.characteristic_value_labels = (
            self.creation_page.characteristic_value_labels
        )
        self.characteristic_buttons = self.creation_page.characteristic_buttons
        self.next_button = self.creation_page.next_button

        self.specialization_back_button = self.specialization_page.back_button
        self.specialization_done_button = self.specialization_page.next_button
        self.specialization_done_button.setEnabled(False)
        self.specialization_scroll = self.specialization_page.scroll_area
        self.specialization_content = self.specialization_page.content
        self.specialization_grid = self.specialization_page.grid
        self.specialization_tiles = self.specialization_page.tiles

        self.outlier_back_button = self.outlier_page.back_button
        self.outlier_done_button = self.outlier_page.done_button
        self.outlier_scroll = self.outlier_page.scroll_area
        self.outlier_content = self.outlier_page.content
        self.outlier_grid = self.outlier_page.grid
        self.outlier_tiles = self.outlier_page.tiles

        self.equipment_page_title = self.equipment_page.title
        self.equipment_back_button = self.equipment_page.back_button
        self.equipment_done_button = self.equipment_page.done_button
        self.equipment_scroll = self.equipment_page.scroll_area
        self.equipment_content = self.equipment_page.content
        self.equipment_grid = self.equipment_page.grid
        self.equipment_tiles = self.equipment_page.tiles
        self.light_aspect_tiles = self.equipment_page.light_aspect_tiles
        self.light_ability_tiles = self.equipment_page.light_ability_tiles
        self._selected_light_category = None
        self._selected_light_aspects = {}
        self._selected_light_powers = {}
        self._selected_light_supers = {}
        self._light_xp_spent = 0
        self._starting_luck = 0
        self.equipment_page.light_category_selected.connect(
            self.select_light_category
        )

        self.create_character_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.character_setup_home)
        )
        self.character_setup_home.version_and_expansions_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.version_and_expansions_page)
        )
        self.character_setup_home.initial_setup_button.clicked.connect(
            self.open_initial_setup_from_home
        )
        self.character_setup_home.stat_point_allocation_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.character_setup_home.outliers_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.character_setup_home.debug_button.clicked.connect(
            self.open_debug_page
        )
        self.character_setup_home.specialization_packs_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.character_setup_home.equipment_or_light_powers_button.clicked.connect(
            self.open_equipment_page
        )
        self.version_and_expansions_page.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.character_setup_home)
        )
        self.version_and_expansions_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )
        self.version_and_expansions_page.continue_button.clicked.connect(
            self.open_initial_setup_from_version
        )
        self.experience_input.valueChanged.connect(self.update_experience_tier)
        self.version_and_expansions_page.mode_changed.connect(
            self._handle_version_selection_changed
        )
        self.upbringing_combo.currentIndexChanged.connect(
            self.refresh_core_background_options
        )
        self.human_combo.currentIndexChanged.connect(self.refresh_selection_options)
        self.guardian_combo.currentIndexChanged.connect(self.update_subclasses)
        self.generate_button.clicked.connect(self.generate_character)
        self.initial_character_setup_page.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.version_and_expansions_page)
        )
        self.initial_character_setup_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )
        self.initial_character_setup_page.option_selected.connect(
            self.select_initial_setup_option
        )
        self.initial_character_setup_page.selection_requirements_changed.connect(
            self.character_setup_home.set_initial_setup_complete
        )
        self.back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.initial_character_setup_page)
        )
        self.creation_points_combo.currentIndexChanged.connect(
            self.reset_creation_points
        )
        self.reset_creation_button.clicked.connect(self.reset_creation_points)
        self.next_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.specialization_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.outlier_page)
        )
        self.specialization_done_button.clicked.connect(
            self.finish_specialization_selection
        )
        self.outlier_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.creation_page)
        )
        self.outlier_done_button.clicked.connect(self.finish_outlier_selection)
        self.equipment_back_button.clicked.connect(
            lambda: self.pages.setCurrentWidget(self.specialization_page)
        )
        self.equipment_done_button.clicked.connect(self.finish_equipment_selection)
        for page in (
            self.creation_page,
            self.specialization_page,
            self.outlier_page,
            self.equipment_page,
        ):
            page.home_button.clicked.connect(self.return_to_character_setup_home)
        self.debug_page.home_button.clicked.connect(
            self.return_to_character_setup_home
        )

        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self._selected_soldier_skills = {}
        self._outlier_characteristics = {}
        # {"upbringing"|"environment": {"name": str, "choices": [label, ...]}}
        self._background_choices = {}
        # {"name": pack_name, "choices": [weapon name, ...]}
        self._equipment_pack_choices = {}
        self._loaded_character_path = None

        self.update_soldier_types()
        self._build_specialization_pack_tiles()
        self._build_outlier_tiles()
        self._build_equipment_tiles()
        self._refresh_initial_setup_options()

    def open_xp_shop(self):
        sheet = self.character_sheet
        self.xp_shop_page.set_character(
            sheet.character_data_for_save(), sheet.ruleset, sheet.game_data
        )
        self.pages.setCurrentWidget(self.xp_shop_page)

    def apply_xp_shop(self, character):
        sheet = self.character_sheet
        sheet.set_character(character, sheet.ruleset, sheet.game_data)
        self.pages.setCurrentWidget(sheet)

    def open_initial_setup_from_home(self):
        self.pages.setCurrentWidget(self.initial_character_setup_page)

    def open_initial_setup_from_version(self):
        self.pages.setCurrentWidget(self.initial_character_setup_page)

    def return_to_character_setup_home(self):
        self.pages.setCurrentWidget(self.character_setup_home)

    @staticmethod
    def _selected_option(combo):
        return combo.currentText() or "None"

    @staticmethod
    def _selected_tile_names(tiles, name_index=1):
        return [
            tile[name_index]
            for tile in tiles
            if tile[0].isChecked()
        ]

    def _selected_outlier_names(self):
        """Selected outliers, one entry per time taken (e.g. Robust twice)."""
        return [
            outlier["name"]
            for tile, outlier, _ in self.outlier_tiles
            if tile.isChecked()
            for _ in range(self._outlier_times(outlier))
        ]

    @property
    def selected_mode(self):
        return self.version_and_expansions_page.selected_mode

    def _create_selection_tile(self, title, text, min_height=125, parent=None):
        card_parent = parent if parent is not None else self.equipment_content
        card = QFrame(card_parent)
        card.setMinimumHeight(min_height)
        card.setStyleSheet(
            theme.TILE_FRAME
        )
        layout = QVBoxLayout(card)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(4)

        select_button = QPushButton(title, card)
        select_button.setCheckable(True)
        select_button.setMinimumSize(260, 72)
        select_button.setStyleSheet(
            theme.SELECT_BUTTON
        )
        layout.addWidget(select_button)

        details_label = QLabel(text, card)
        details_label.setWordWrap(True)
        details_label.setStyleSheet(
            theme.TILE_TEXT
        )
        layout.addWidget(details_label)

        select_button.toggled.connect(
            lambda checked, selected_card=card: selected_card.setStyleSheet(
                "QFrame { background-color: #242424; "
                + (
                    "border: 3px solid #f7d36b;"
                    if checked
                    else "border: 2px solid #526b28;"
                )
                + " border-radius: 8px; }"
            )
        )
        return card, select_button

    # ---------------------------------------------------------
    # Generate character
    # ---------------------------------------------------------
    def generate_character(self):
        self.character_setup_home.set_character_ready_to_export(False)
        name = "Test Character"
        use_lns = self.selected_mode == "Light & Sky"
        if not use_lns and not self._ensure_background_choices():
            return
        if use_lns:
            human_type = self.human_combo.currentData()
            guardian_type = self.guardian_combo.currentData()
            soldier_type = guardian_type or human_type
            subclass = self.subclass_combo.currentText() or None
            if not guardian_type:
                subclass = None
            connection = self.connection_combo.currentText() or None
        else:
            soldier_type = self.soldier_combo.currentData()
            self._selected_core_soldier = soldier_type
            subclass = None
            connection = None

        generator = CharacterGenerator(self.game_data, use_light_and_sky=use_lns)
        selected_soldier_types = (
            [human_type, guardian_type]
            if use_lns
            else [soldier_type]
        )
        skill_training = {}
        for selected_type in selected_soldier_types:
            for skill, bonus in self._selected_soldier_skills.get(
                selected_type, {}
            ).items():
                skill_training[skill] = max(
                    skill_training.get(skill, 0), bonus
                )

        try:
            char = generator.generate(
                name=name,
                soldier_type=soldier_type,
                subclass=subclass,
                human_soldier_type=human_type if use_lns else None,
                guardian_class=guardian_type if use_lns else None,
                connection=connection,
                upbringing=(self.upbringing_combo.currentData() if not use_lns else None),
                environment=(self.environment_combo.currentData() if not use_lns else None),
                upbringing_choices=(
                    self._background_choices_for(
                        "upbringing", self.upbringing_combo.currentData()
                    )
                    if not use_lns
                    else None
                ),
                environment_choices=(
                    self._background_choices_for(
                        "environment", self.environment_combo.currentData()
                    )
                    if not use_lns
                    else None
                ),
                lifestyle_choice=self._choose_lifestyle_options,
                lifestyles=(
                    [combo.currentData() for combo in self.lifestyle_combos if combo.currentData()]
                    if not use_lns
                    else None
                ),
                starting_experience=self.experience_input.value(),
                skill_training=skill_training or None,
            )
        except CreationCancelled:
            return

        self.generated_character = char
        self._pre_outlier_mythic_characteristics = (
            char.mythic_characteristics.copy()
        )
        self._outlier_characteristics.clear()

        # Reset per-character creation state so a regenerated character
        # never inherits selections from the previous one.
        for attr in ("_pre_specialization_skills", "_pre_specialization_abilities"):
            if hasattr(self, attr):
                delattr(self, attr)
        self._light_xp_spent = 0
        self._equipment_pack_choices = {}
        self._selected_light_category = None
        self._selected_light_aspects = {}
        self._selected_light_powers = {}
        self._selected_light_supers = {}
        self._reset_outlier_tiles()
        for button, _ in self.specialization_tiles:
            button.blockSignals(True)
            button.setChecked(False)
            button.blockSignals(False)

        if use_lns:
            self._build_light_power_tiles()
        else:
            self._build_equipment_tiles()
        self._generated_characteristics = char.characteristics.copy()
        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self._build_characteristic_controls()

        self._update_creation_point_display()
        self.pages.setCurrentWidget(self.creation_page)

    # ---------------------------------------------------------
    # Start over
    # ---------------------------------------------------------
    def discard_character_creation(self):
        has_changes = (
            self.experience_input.value() > 0
            or self.selected_mode is not None
            or hasattr(self, "generated_character")
        )
        if has_changes:
            answer = QMessageBox.question(
                self,
                "Discard Character?",
                "Discard all changes to this character and return to the main page?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return
        self.reset_character_creator()
        self.pages.setCurrentWidget(self.landing_page)

    def reset_character_creator(self):
        """Return every creator page to its state on a new window."""
        # Drop the character and mode first: the combo and spin box signals
        # fired below act on whichever of them still exist.
        for attr in (
            "generated_character",
            "_generated_characteristics",
            "_pre_outlier_mythic_characteristics",
            "_pre_specialization_skills",
            "_pre_specialization_abilities",
        ):
            if hasattr(self, attr):
                delattr(self, attr)
        self.version_and_expansions_page.clear_selection()

        self._selected_core_soldier = None
        self._background_choices = {}
        self._outlier_characteristics = {}
        self._equipment_pack_choices = {}
        self._light_xp_spent = 0
        self._selected_light_category = None
        self._selected_light_aspects = {}
        self._selected_light_powers = {}
        self._selected_light_supers = {}

        # With no mode selected, the refresh below leaves these untouched.
        for combo in (
            self.upbringing_combo,
            self.environment_combo,
            *self.lifestyle_combos,
        ):
            combo.clear()

        self._clear_creation_points()
        self.experience_input.setValue(0)
        self._handle_version_selection_changed(None)
        self._build_specialization_pack_tiles()
        self.equipment_page.clear_selection()
        self.update_equipment_selection()
        self.initial_character_setup_page.select_category("soldier")


# Backwards-compatible name for older imports.
TestGeneratorUI = MainWindow


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.showMaximized()
    sys.exit(app.exec())
