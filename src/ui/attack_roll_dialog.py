"""Window that rolls To Hit Tests for the Attack Calculator."""

import random
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from src.models import dice
from src.ui import theme

AIM_LABELS = {"Half Aim": 1, "Full Aim": 2}  # attacks the Aim bonus applies to
AIM_BONUS_LABELS = ("Half Aim", "Full Aim", "Steady Aim")
SUCCESS_COLOR = "#9fd36b"
FAILURE_COLOR = "#e08a7a"


def outcome_color(result: dice.TestResult) -> str:
    if result.critical == "success":
        return theme.HIGHLIGHT
    return SUCCESS_COLOR if result.success else FAILURE_COLOR


def plan_attacks(result, count: int) -> list:
    """Target number for each attack: Aim only helps the first one (Half) or two (Full)."""
    aim_count = next((AIM_LABELS[label] for label, _ in result.modifiers if label in AIM_LABELS), 0)
    aim_bonus = sum(value for label, value in result.modifiers if label in AIM_BONUS_LABELS)
    return [result.total if index < aim_count else result.total - aim_bonus for index in range(count)]


def called_shot_penalty(result) -> int:
    return sum(value for label, value in result.modifiers if label.startswith("Called Shot"))


def describe_hit(test: dice.TestResult, roll_target: int, called_penalty: int) -> str:
    """Where a To Hit roll strikes, following the Called Shot and Critical rules."""
    location, sublocation, reversed_roll = dice.hit_location(test.roll)
    random_hit = f"{location} ({sublocation}, {reversed_roll:02d})"
    if test.critical == "success":
        return "You choose where it hits (Critical Success)"
    if test.success:
        return "The called location" if called_penalty else random_hit
    if called_penalty and test.critical is None:
        # A missed Called Shot still hits if it would have hit with 2 Degrees of Success without it
        without = dice.resolve_test(test.roll, roll_target - called_penalty)
        if without.success and without.degrees >= 2:
            return f"Missed the called location but still hits: {random_hit}"
    return "Miss"


class AttackRollDialog(QDialog):
    def __init__(self, title, result, rng: Optional[random.Random] = None, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Attack Roll - {title}")
        self.setMinimumWidth(640)
        self.result = result
        self.rng = rng or random.Random()
        self.tests: list = []

        layout = QVBoxLayout(self)
        heading = QLabel(title)
        heading.setStyleSheet(theme.SECTION_HEADING)
        layout.addWidget(heading)
        modifier = result.total_modifier
        self.target_label = QLabel(
            f"Rolling against <b>{result.total}</b> "
            f"({result.characteristic_name} {result.characteristic}"
            + (f" {modifier:+d}" if modifier else "") + ")"
        )
        layout.addWidget(self.target_label)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Attacks"))
        self.count_input = QSpinBox()
        self.count_input.setRange(1, 30)
        self.count_input.setToolTip(
            "How many To Hit Tests to roll, e.g. Semi-Auto (3) makes 3 Attacks per Half Action. "
            "Burst and Sustained fire make a single Test."
        )
        controls.addWidget(self.count_input)
        self.roll_button = QPushButton("Roll Again")
        self.roll_button.clicked.connect(self.roll)
        controls.addWidget(self.roll_button)
        controls.addStretch(1)
        layout.addLayout(controls)

        self.summary_label = QLabel("")
        self.summary_label.setStyleSheet("font-size: 22px; font-weight: bold;")
        self.summary_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.summary_label)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(("#", "Target", "Roll", "Result", "Degrees", "Hit Location"))
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table.horizontalHeader()
        for column in range(5):
            header.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table)

        self.notes_label = QLabel("")
        self.notes_label.setWordWrap(True)
        self.notes_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(self.notes_label)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.count_input.valueChanged.connect(self.roll)
        self.roll()

    def roll(self, *_):
        called = called_shot_penalty(self.result)
        targets = plan_attacks(self.result, self.count_input.value())
        self.tests = []
        self.table.setRowCount(0)
        for index, target in enumerate(targets):
            test = dice.resolve_test(dice.roll_d100(self.rng), target, self.result.characteristic)
            hit = describe_hit(test, target, called)
            self.tests.append((test, hit))
            self.table.insertRow(index)
            cells = (str(index + 1), str(target), f"{test.roll:02d}", test.outcome, test.degrees_text, hit)
            for column, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if column in (3, 4):
                    item.setForeground(_brush(outcome_color(test)))
                if column < 5:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(index, column, item)

        first = self.tests[0][0]
        if len(self.tests) == 1:
            self.summary_label.setText(
                f"Rolled <b>{first.roll:02d}</b>: <span style='color:{outcome_color(first)}'>"
                f"{first.outcome}</span>, {first.degrees_text}"
            )
        else:
            hits = sum(1 for test, hit in self.tests if hit != "Miss")
            self.summary_label.setText(f"{hits} of {len(self.tests)} Attacks hit")
        self.table.setFixedHeight(
            self.table.horizontalHeader().height() + 6
            + sum(self.table.rowHeight(r) for r in range(self.table.rowCount()))
        )

        notes = []
        if any(test.critical == "success" for test, _ in self.tests):
            notes.append("Critical Success: the Attack deals maximum Damage (all 10s on D10s, 5s on D5s).")
        if any(test.critical == "failure" for test, _ in self.tests):
            notes.append("Critical Failure (natural 100): the GM picks a fitting consequence.")
        if len(targets) > 1 and len(set(targets)) > 1:
            notes.append("The Aim bonus only applies to the first Attack (Half Aim) or first two (Full Aim).")
        notes.append("Hit Location is the roll with its digits reversed. The target may still Evade or Parry.")
        self.notes_label.setText("\n".join(notes))


def _brush(color: str):
    from PySide6.QtGui import QBrush, QColor

    return QBrush(QColor(color))
