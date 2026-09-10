from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QTextEdit
)
import sys

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator


class TestGeneratorUI(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Mythic Character Generator Test UI")
        self.resize(700, 550)

        layout = QVBoxLayout()
        self.setLayout(layout)

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
        layout.addLayout(mode_row)

        # ---------------------------------------------------------
        # Core soldier type selection
        # ---------------------------------------------------------
        st_row = QHBoxLayout()
        st_label = QLabel("Soldier Type:")
        self.soldier_combo = QComboBox()

        st_row.addWidget(st_label)
        st_row.addWidget(self.soldier_combo)
        layout.addLayout(st_row)
        self.core_soldier_row = st_row
        self.soldier_label = st_label

        # ---------------------------------------------------------
        # Light & Sky soldier type selections
        # ---------------------------------------------------------
        human_row = QHBoxLayout()
        self.human_label = QLabel("Human Soldier Type:")
        self.human_combo = QComboBox()
        human_row.addWidget(self.human_label)
        human_row.addWidget(self.human_combo)
        layout.addLayout(human_row)

        guardian_row = QHBoxLayout()
        self.guardian_label = QLabel("Guardian Class Soldier Type:")
        self.guardian_combo = QComboBox()
        self.guardian_combo.currentIndexChanged.connect(self.update_subclasses)
        guardian_row.addWidget(self.guardian_label)
        guardian_row.addWidget(self.guardian_combo)
        layout.addLayout(guardian_row)

        # ---------------------------------------------------------
        # Subclass selection (only for Guardian classes)
        # ---------------------------------------------------------
        sub_row = QHBoxLayout()
        sub_label = QLabel("Subclass:")
        self.subclass_combo = QComboBox()

        sub_row.addWidget(sub_label)
        sub_row.addWidget(self.subclass_combo)
        layout.addLayout(sub_row)
        self.subclass_label = sub_label

        self.human_row_widgets = (self.human_label, self.human_combo)
        self.guardian_row_widgets = (self.guardian_label, self.guardian_combo)

        # ---------------------------------------------------------
        # Generate button
        # ---------------------------------------------------------
        self.generate_button = QPushButton("Generate Character")
        self.generate_button.clicked.connect(self.generate_character)
        layout.addWidget(self.generate_button)

        # ---------------------------------------------------------
        # Output log
        # ---------------------------------------------------------
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        layout.addWidget(self.output)

        # Load initial data
        self.update_soldier_types()

    # ---------------------------------------------------------
    # Load soldier types based on mode
    # ---------------------------------------------------------
    def update_soldier_types(self):
        use_lns = self.mode_combo.currentText() == "Light & Sky"
        loader = DataLoader(use_light_and_sky=use_lns)
        self.game_data = loader.load_all()

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

        self.soldier_combo.clear()
        self.human_combo.clear()
        self.guardian_combo.clear()
        self.subclass_combo.clear()

        if use_lns:
            self.human_combo.addItem("")
            self.human_combo.addItems(human_list)
            self.guardian_combo.addItem("")
            self.guardian_combo.addItems(guardian_list)
        else:
            self.soldier_combo.addItems(core_list)

        self.soldier_combo.setVisible(not use_lns)
        self.soldier_label.setVisible(not use_lns)
        for widget in self.human_row_widgets:
            widget.setVisible(use_lns)
        for widget in self.guardian_row_widgets:
            widget.setVisible(use_lns)
        self.subclass_combo.setVisible(use_lns)
        self.subclass_label.setVisible(use_lns)

        self.update_subclasses()

    # ---------------------------------------------------------
    # Populate subclasses when a Guardian class is selected
    # ---------------------------------------------------------
    def update_subclasses(self):
        self.subclass_combo.clear()

        soldier_type = self.guardian_combo.currentText()
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
            human_type = self.human_combo.currentText()
            guardian_type = self.guardian_combo.currentText()
            soldier_type = guardian_type or human_type
            subclass = self.subclass_combo.currentText() or None
            if not guardian_type:
                subclass = None
        else:
            soldier_type = self.soldier_combo.currentText()
            subclass = None

        generator = CharacterGenerator(self.game_data, use_light_and_sky=use_lns)

        char = generator.generate(
            name=name,
            soldier_type=soldier_type,
            subclass=subclass,
            human_soldier_type=human_type if use_lns else None,
            guardian_class=guardian_type if use_lns else None,
        )

        # Show debug log
        self.output.clear()
        for line in char.debug_log:
            self.output.append(line)


# ---------------------------------------------------------
# Run UI
# ---------------------------------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestGeneratorUI()
    window.show()
    sys.exit(app.exec())
