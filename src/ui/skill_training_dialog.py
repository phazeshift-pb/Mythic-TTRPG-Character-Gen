from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QVBoxLayout,
)


class SkillTrainingDialog(QDialog):
    def __init__(
        self,
        skill_names,
        skill_count,
        training_bonus,
        selected_skills=(),
        parent=None,
        title="Choose Skill Training",
        noun="skills",
        training_label=None,
    ):
        """Pick exactly ``skill_count`` names from a list.

        Also used for a Soldier Type's starting Educations (``noun="Educations"``).
        """
        super().__init__(parent)
        if skill_count < 1 or skill_count > len(skill_names):
            raise ValueError(f"The {noun} count is outside the available list.")

        self.setWindowTitle(title)
        self.setMinimumWidth(360)
        layout = QVBoxLayout(self)
        if training_label is None:
            training_label = (
                "Trained" if training_bonus == 0 else f"+{training_bonus}"
            )
        singular = noun[:-1] if noun.endswith("s") else noun
        layout.addWidget(
            QLabel(
                f"Choose exactly {skill_count} {noun}. "
                f"Each selected {singular} starts at {training_label}."
            )
        )

        self.skill_list = QListWidget(self)
        self.skill_list.setMinimumHeight(260)
        for skill_name in skill_names:
            item = QListWidgetItem(skill_name)
            item.setData(Qt.ItemDataRole.UserRole, skill_name)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked
                if skill_name in selected_skills
                else Qt.CheckState.Unchecked
            )
            self.skill_list.addItem(item)
        layout.addWidget(self.skill_list)

        self.selection_count = QLabel()
        layout.addWidget(self.selection_count)
        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            parent=self,
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        self.skill_count = skill_count
        self.skill_list.itemChanged.connect(self._update_selection_count)
        self._update_selection_count()

    @property
    def selected_skills(self):
        return [
            self.skill_list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.skill_list.count())
            if self.skill_list.item(index).checkState()
            == Qt.CheckState.Checked
        ]

    def _update_selection_count(self, item=None):
        selected_count = len(self.selected_skills)
        if selected_count > self.skill_count and item is not None:
            self.skill_list.blockSignals(True)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.skill_list.blockSignals(False)
            selected_count -= 1

        self.selection_count.setText(
            f"Selected: {selected_count} / {self.skill_count}"
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            selected_count == self.skill_count
        )
