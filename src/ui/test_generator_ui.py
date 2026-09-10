from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit, QSpinBox,
    QStackedWidget, QGridLayout
)
import sys

from PySide6.QtCore import Qt
from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.character import CHAR_CODES


class TestGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mythic Character Generator Test UI")
        self.resize(700, 550)

        layout = QVBoxLayout()
        self.setLayout(layout)

        self.pages = QStackedWidget()
        layout.addWidget(self.pages)
        self.selection_page = QWidget()
        self.selection_layout = QVBoxLayout(self.selection_page)
        self.pages.addWidget(self.selection_page)

        # ---------------------------------------------------------
        # Starting experience and automatic tier
        # ---------------------------------------------------------
        experience_row = QHBoxLayout()
        experience_label = QLabel("Starting XP:")
        self.experience_input = QSpinBox()
        self.experience_input.setRange(0, 10_000_000)
        self.experience_input.setValue(0)
        self.experience_input.valueChanged.connect(self.update_experience_tier)
        self.experience_tier_label = QLabel("Tier: 0")
        experience_row.addWidget(experience_label)
        experience_row.addWidget(self.experience_input)
        experience_row.addWidget(self.experience_tier_label)
        self.selection_layout.addLayout(experience_row)

        # ---------------------------------------------------------
        # Mode selection (Core vs Light & Sky)
        # ---------------------------------------------------------
        mode_row = QHBoxLayout()
        mode_label = QLabel("Mode:")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Core", "Light & Sky"])
        self.mode_combo.currentIndexChanged.connect(self.update_soldier_types)

        mode_row.addWidget(mode_label)
        mode_row.addWidget(self.mode_combo)
        self.selection_layout.addLayout(mode_row)

        # ---------------------------------------------------------
        # Core soldier type selection
        # ---------------------------------------------------------
        st_row = QHBoxLayout()
        st_label = QLabel("Soldier Type:")
        self.soldier_combo = QComboBox()

        st_row.addWidget(st_label)
        st_row.addWidget(self.soldier_combo)
        self.selection_layout.addLayout(st_row)
        self.core_soldier_row = st_row
        self.soldier_label = st_label

        # ---------------------------------------------------------
        # Light & Sky soldier type selections
        # ---------------------------------------------------------
        human_row = QHBoxLayout()
        self.human_label = QLabel("Human Soldier Type:")
        self.human_combo = QComboBox()
        self.human_combo.currentIndexChanged.connect(self.refresh_selection_options)
        human_row.addWidget(self.human_label)
        human_row.addWidget(self.human_combo)
        self.selection_layout.addLayout(human_row)

        guardian_row = QHBoxLayout()
        self.guardian_label = QLabel("Guardian Class Soldier Type:")
        self.guardian_combo = QComboBox()
        self.guardian_combo.currentIndexChanged.connect(self.update_subclasses)
        guardian_row.addWidget(self.guardian_label)
        guardian_row.addWidget(self.guardian_combo)
        self.selection_layout.addLayout(guardian_row)

        # ---------------------------------------------------------
        # Subclass selection (only for Guardian classes)
        # ---------------------------------------------------------
        sub_row = QHBoxLayout()
        sub_label = QLabel("Subclass:")
        self.subclass_combo = QComboBox()

        sub_row.addWidget(sub_label)
        sub_row.addWidget(self.subclass_combo)
        self.selection_layout.addLayout(sub_row)
        self.subclass_label = sub_label

        connection_row = QHBoxLayout()
        self.connection_label = QLabel("Connection:")
        self.connection_combo = QComboBox()
        connection_row.addWidget(self.connection_label)
        connection_row.addWidget(self.connection_combo)
        self.selection_layout.addLayout(connection_row)

        self.human_row_widgets = (self.human_label, self.human_combo)
        self.guardian_row_widgets = (self.guardian_label, self.guardian_combo)

        # ---------------------------------------------------------
        # Generate button
        # ---------------------------------------------------------
        self.generate_button = QPushButton("Generate Character")
        self.generate_button.clicked.connect(self.generate_character)
        self.selection_layout.addWidget(self.generate_button)

        # ---------------------------------------------------------
        # Creation point allocation page
        # ---------------------------------------------------------
        self.creation_page = QWidget()
        creation_layout = QVBoxLayout(self.creation_page)
        self.pages.addWidget(self.creation_page)

        creation_header = QHBoxLayout()
        self.back_button = QPushButton("Back")
        self.back_button.clicked.connect(lambda: self.pages.setCurrentWidget(self.selection_page))
        self.creation_points_combo = QComboBox()
        self.creation_points_combo.currentIndexChanged.connect(self.reset_creation_points)
        self.reset_creation_button = QPushButton("Reset Points")
        self.reset_creation_button.clicked.connect(self.reset_creation_points)
        self.creation_points_remaining_label = QLabel("Points remaining: 0")
        creation_header.addWidget(self.back_button)
        creation_header.addWidget(QLabel("Creation points:"))
        creation_header.addWidget(self.creation_points_combo)
        creation_header.addWidget(self.reset_creation_button)
        creation_header.addWidget(self.creation_points_remaining_label)
        creation_layout.addLayout(creation_header)

        self.characteristic_grid = QGridLayout()
        self.characteristic_value_labels = {}
        self.characteristic_buttons = {}
        creation_layout.addLayout(self.characteristic_grid)

        # Output log
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        creation_layout.addWidget(self.output)

        # Load initial data
        self.update_soldier_types()

    def reset_creation_points(self):
        if not hasattr(self, "generated_character"):
            return

        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self.generated_character.characteristics = self._generated_characteristics.copy()
        self._update_creation_point_display()

    def adjust_creation_points(self, code, amount):
        if not hasattr(self, "generated_character"):
            return

        current = self._creation_allocations[code]
        total_points = self.creation_points_combo.currentData()
        spent = sum(self._creation_allocations.values())

        if amount > 0 and (spent >= total_points or current >= self._max_creation_points):
            return
        if amount < 0 and current <= 0:
            return

        self._creation_allocations[code] = current + amount
        self.generated_character.characteristics[code] += amount
        self._update_creation_point_display()

    def _update_creation_point_display(self):
        spent = sum(self._creation_allocations.values())
        total_points = self.creation_points_combo.currentData() or 0
        self.creation_points_remaining_label.setText(
            f"Points remaining: {total_points - spent}"
        )

        for code, value_label in self.characteristic_value_labels.items():
            value_label.setText(str(self.generated_character.characteristics[code]))
            minus_button, plus_button = self.characteristic_buttons[code]
            minus_button.setEnabled(self._creation_allocations[code] > 0)
            plus_button.setEnabled(
                spent < total_points
                and self._creation_allocations[code] < self._max_creation_points
            )

    def _load_creation_point_options(self):
        document = self.game_data.get("creation_points", "creation_points") or {}
        points = document.get("creation_points", {})
        self.creation_points_combo.clear()
        self.creation_points_combo.addItem(
            f"Base ({points.get('base_points', 85)} points)",
            points.get("base_points", 85),
        )
        self.creation_points_combo.addItem(
            f"High Power ({points.get('high_power_option', 100)} points)",
            points.get("high_power_option", 100),
        )
        self._max_creation_points = points.get("max_per_characteristic", 20)

    def _build_characteristic_controls(self):
        while self.characteristic_grid.count():
            item = self.characteristic_grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.characteristic_value_labels.clear()
        self.characteristic_buttons.clear()
        for column, code in enumerate(CHAR_CODES):
            self.characteristic_grid.addWidget(QLabel(code), 0, column)
            value_label = QLabel("0")
            value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.characteristic_grid.addWidget(value_label, 1, column)
            minus_button = QPushButton("-")
            plus_button = QPushButton("+")
            minus_button.clicked.connect(lambda checked=False, c=code: self.adjust_creation_points(c, -1))
            plus_button.clicked.connect(lambda checked=False, c=code: self.adjust_creation_points(c, 1))
            self.characteristic_grid.addWidget(plus_button, 2, column)
            self.characteristic_grid.addWidget(minus_button, 3, column)
            self.characteristic_value_labels[code] = value_label
            self.characteristic_buttons[code] = (minus_button, plus_button)

    def update_experience_tier(self):
        if not hasattr(self, "game_data"):
            return

        tiers_document = self.game_data.get("experience_tiers", "experience_tiers") or {}
        tiers = tiers_document.get("experience_tiers", {}).get("tiers", [])
        experience = self.experience_input.value()
        tier_number = 0

        for tier in tiers:
            xp_range = tier.get("xp", "")
            if "+" in xp_range:
                lower_bound = int(xp_range.replace("+", "").replace(",", ""))
                if experience >= lower_bound:
                    tier_number = tier["tier"]
            else:
                bounds = xp_range.replace("–", "-").replace(",", "").split("-")
                if len(bounds) == 2 and int(bounds[0]) <= experience <= int(bounds[1]):
                    tier_number = tier["tier"]

        self.experience_tier_label.setText(f"Tier: {tier_number}")
        self.refresh_selection_options()

    # ---------------------------------------------------------
    # Load soldier types based on mode
    # ---------------------------------------------------------
    def update_soldier_types(self):
        use_lns = self.mode_combo.currentText() == "Light & Sky"
        loader = DataLoader(use_light_and_sky=use_lns)
        self.game_data = loader.load_all()
        self._load_creation_point_options()
        self.update_experience_tier()

        soldier_types = self.game_data.families.get("soldier_type", {})

        core_list = []
        human_list = []
        guardian_list = []

        for name, record in soldier_types.items():
            path = record.get("source_path", "")

            if "core/unsc_soldier_types" in path:
                core_list.append(name)

            if "light_and_sky/character_creation/human_soldier_types" in path:
                human_list.append(name)

            if "light_and_sky/character_creation/guardian_classes_subclasses" in path:
                guardian_list.append(name)

        self._core_names = core_list
        self._human_names = human_list
        self._guardian_names = guardian_list
        self.subclass_combo.clear()
        self.connection_combo.clear()

        if use_lns:
            self.connection_combo.addItem("")
            connections = self.game_data.get("connections", "connections") or {}
            connections = connections.get("connections", connections)
            for category in ("light", "darkness", "specialized"):
                self.connection_combo.addItems(
                    item["name"] for item in connections.get(category, [])
                )
        self.soldier_combo.setVisible(not use_lns)
        self.soldier_label.setVisible(not use_lns)
        for widget in self.human_row_widgets:
            widget.setVisible(use_lns)
        for widget in self.guardian_row_widgets:
            widget.setVisible(use_lns)
        self.subclass_combo.setVisible(use_lns)
        self.subclass_label.setVisible(use_lns)
        self.connection_combo.setVisible(use_lns)
        self.connection_label.setVisible(use_lns)

        self.refresh_selection_options()
        self.update_subclasses()

    @staticmethod
    def _add_costed_items(combo, names, records, available_xp):
        combo.addItem("")
        for name in names:
            cost = records[name].get("experience_cost", 0)
            if cost <= available_xp:
                combo.addItem(f"{records[name].get('name', name)} ({cost:,} XP)", name)

    def refresh_selection_options(self):
        if (
            not hasattr(self, "game_data")
            or not hasattr(self, "_core_names")
            or getattr(self, "_refreshing_options", False)
        ):
            return

        self._refreshing_options = True
        try:
            records = self.game_data.families.get("soldier_type", {})
            available_xp = self.experience_input.value()
            use_lns = self.mode_combo.currentText() == "Light & Sky"
            selected_human = self.human_combo.currentData()
            selected_guardian = self.guardian_combo.currentData()

            self.soldier_combo.clear()
            self.human_combo.clear()
            self.guardian_combo.clear()

            if use_lns:
                self._add_costed_items(
                    self.human_combo, self._human_names, records, available_xp
                )
                human_cost = records.get(selected_human, {}).get("experience_cost", 0)
                guardian_xp = max(0, available_xp - human_cost)
                self._add_costed_items(
                    self.guardian_combo, self._guardian_names, records, guardian_xp
                )
                self._restore_combo_selection(self.human_combo, selected_human)
                self._restore_combo_selection(self.guardian_combo, selected_guardian)
            else:
                self._add_costed_items(
                    self.soldier_combo, self._core_names, records, available_xp
                )
            if use_lns:
                self.update_subclasses()
        finally:
            self._refreshing_options = False

    @staticmethod
    def _restore_combo_selection(combo, key):
        if key is None:
            return
        index = combo.findData(key)
        if index >= 0:
            combo.setCurrentIndex(index)

    # ---------------------------------------------------------
    # Populate subclasses when a Guardian class is selected
    # ---------------------------------------------------------
    def update_subclasses(self):
        self.subclass_combo.clear()

        soldier_type = self.guardian_combo.currentData()
        if not soldier_type:
            return

        record = self.game_data.get("soldier_type", soldier_type)
        if not record:
            return

        path = record.get("source_path", "")

        # Only Guardian classes have subclasses
        if "guardian_classes_subclasses" in path:
            subclasses = record.get("subclasses", {})
            self.subclass_combo.addItems(list(subclasses.keys()))
        else:
            # No subclasses for UNSC or Human soldier types
            self.subclass_combo.clear()

    # ---------------------------------------------------------
    # Generate character
    # ---------------------------------------------------------
    def generate_character(self):
        name = "Test Character"
        use_lns = self.mode_combo.currentText() == "Light & Sky"
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
            subclass = None
            connection = None

        generator = CharacterGenerator(self.game_data, use_light_and_sky=use_lns)

        char = generator.generate(
            name=name,
            soldier_type=soldier_type,
            subclass=subclass,
            human_soldier_type=human_type if use_lns else None,
            guardian_class=guardian_type if use_lns else None,
            connection=connection,
            starting_experience=self.experience_input.value(),
        )

        self.generated_character = char
        self._generated_characteristics = char.characteristics.copy()
        self._creation_allocations = {code: 0 for code in CHAR_CODES}
        self._build_characteristic_controls()

        # Show debug log
        self.output.clear()
        for line in char.debug_log:
            self.output.append(line)
        self._update_creation_point_display()
        self.pages.setCurrentWidget(self.creation_page)


# ---------------------------------------------------------
# Run UI
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestGeneratorUI()
    window.show()
    sys.exit(app.exec())
