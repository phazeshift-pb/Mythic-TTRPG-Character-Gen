"""XP Shop page: spend a loaded character's Experience after creation.

Opened from the character sheet's Spend XP button. The page works on a copy
of the character; Apply hands the changed copy back to the sheet (press Save
there to write the file) and Cancel throws it away. Rules live in
src/models/xp_shop.py.
"""

from typing import Any

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from src.models.xp_shop import LIGHT_AND_SKY, PurchaseError, XpShop, snapshot
from src.ui import theme

COLUMNS = ("Purchase", "Current", "Next", "XP Cost", "Status", "")


class XpShopPage(QWidget):
    applied = Signal(object)
    cancelled = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.character: dict[str, Any] = {}
        self.game_data = None
        self.ruleset = ""
        self.shop: XpShop | None = None
        self._history: list[tuple[dict, str]] = []
        self._items = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.title = QLabel("XP SHOP")
        self.title.setStyleSheet(theme.APP_TITLE)
        self.subtitle = QLabel("")
        self.subtitle.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        titles.addWidget(self.title)
        titles.addWidget(self.subtitle)
        header.addLayout(titles, 1)

        self.xp_label = QLabel("")
        self.xp_label.setStyleSheet(
            f"font-size: 18px; font-weight: bold; color: {theme.HIGHLIGHT}; padding: 0 16px;"
        )
        header.addWidget(self.xp_label)

        self.gm_override = QCheckBox("GM approval")
        self.gm_override.setToolTip(
            "Allow purchases the GM has to sign off on: restricted Educations, "
            "Forerunner training, Specialized Connections, ORION augmentation and "
            "prerequisites the app can't check (Luck, Traits)."
        )
        self.gm_override.toggled.connect(self._refresh_items)
        header.addWidget(self.gm_override)

        self.undo_button = QPushButton("Undo")
        self.undo_button.clicked.connect(self.undo)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(lambda: self.cancelled.emit())
        self.apply_button = QPushButton("Apply to Sheet")
        self.apply_button.setToolTip("Return to the character sheet with these purchases. Press Save there to keep them.")
        self.apply_button.clicked.connect(lambda: self.applied.emit(self.character))
        for button in (self.undo_button, self.cancel_button, self.apply_button):
            header.addWidget(button)
        layout.addLayout(header)

        self.note_label = QLabel(
            "Spend Experience between Missions or at a GM checkpoint. Core purchases are "
            "open to every character; Light & Sky purchases appear only for Light & Sky characters."
        )
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet(f"color: {theme.TEXT_MUTED};")
        layout.addWidget(self.note_label)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.category_list = QListWidget()
        self.category_list.setMaximumWidth(220)
        self.category_list.setStyleSheet(
            "QListWidget { font-size: 15px; font-weight: bold; }"
            "QListWidget::item { padding: 8px; }"
            f"QListWidget::item:selected {{ background-color: {theme.GREEN_DARK}; "
            f"border: 2px solid {theme.HIGHLIGHT}; }}"
        )
        self.category_list.currentRowChanged.connect(self._refresh_items)
        splitter.addWidget(self.category_list)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(8, 0, 0, 0)
        filters = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search...")
        self.search_input.textChanged.connect(self._refresh_items)
        self.show_unavailable = QCheckBox("Show unavailable")
        self.show_unavailable.setChecked(True)
        self.show_unavailable.toggled.connect(self._refresh_items)
        self.affordable_only = QCheckBox("Affordable only")
        self.affordable_only.toggled.connect(self._refresh_items)
        filters.addWidget(self.search_input, 1)
        filters.addWidget(self.show_unavailable)
        filters.addWidget(self.affordable_only)
        right_layout.addLayout(filters)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for column in range(1, len(COLUMNS)):
            header_view.setSectionResizeMode(column, QHeaderView.ResizeMode.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.currentCellChanged.connect(lambda row, *_: self._show_details(row))
        right_layout.addWidget(self.table, 1)

        self.details_label = QLabel("Select a purchase to see its rules.")
        self.details_label.setWordWrap(True)
        self.details_label.setMinimumHeight(70)
        self.details_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.details_label.setStyleSheet(
            f"QLabel {{ background-color: {theme.BACKGROUND}; border: 1px solid {theme.GREEN}; "
            "border-radius: 6px; padding: 8px; }"
        )
        right_layout.addWidget(self.details_label)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        history_title = QLabel("Purchases this visit")
        history_title.setStyleSheet(theme.SUBHEADING)
        layout.addWidget(history_title)
        self.history_list = QListWidget()
        self.history_list.setMaximumHeight(110)
        layout.addWidget(self.history_list)

    # ---------------------------------------------------------
    # Setup
    # ---------------------------------------------------------
    def set_character(self, character: dict[str, Any], ruleset: str = "", game_data=None):
        self.character = snapshot(character)
        self.ruleset = ruleset or ""
        self.game_data = game_data
        self.shop = XpShop(self.character, game_data, self.ruleset)
        self._history = []
        self.history_list.clear()
        self.gm_override.setChecked(False)
        self.search_input.clear()
        name = character.get("name") or "Unnamed Character"
        self.title.setText(f"XP SHOP - {name}")
        self.subtitle.setText(
            f"{self.ruleset or 'Core'} | {character.get('soldier_type') or 'Unknown Soldier Type'}"
        )

        self.category_list.blockSignals(True)
        self.category_list.clear()
        for category in self.shop.categories():
            label = category
            if self.ruleset == LIGHT_AND_SKY and category in (
                "Connections", "Light Slots", "Light Aspects", "Light Abilities", "Supers"
            ):
                label = f"{category}  (L&S)"
            self.category_list.addItem(label)
        self.category_list.blockSignals(False)
        self.category_list.setCurrentRow(0)
        self._refresh_items()

    def current_category(self) -> str:
        if self.shop is None:
            return ""
        row = self.category_list.currentRow()
        categories = self.shop.categories()
        return categories[row] if 0 <= row < len(categories) else ""

    # ---------------------------------------------------------
    # Table
    # ---------------------------------------------------------
    def _refresh_items(self, *_):
        self._update_header()
        self.table.setRowCount(0)
        self._items = []
        if self.shop is None:
            return
        query = self.search_input.text().strip().casefold()
        gm = self.gm_override.isChecked()
        for item in self.shop.items(self.current_category()):
            allowed, reason = self.shop.can_buy(item, gm)
            if query and query not in f"{item.name} {item.description} {item.next}".casefold():
                continue
            if not allowed and not self.show_unavailable.isChecked():
                continue
            if self.affordable_only.isChecked() and item.cost > self.shop.available_xp:
                continue
            self._add_row(item, allowed, reason)
        self.table.resizeRowsToContents()
        if self.table.rowCount():
            self.table.selectRow(0)
        else:
            self.details_label.setText("Nothing to show with these filters.")

    def _add_row(self, item, allowed, reason):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self._items.append(item)
        cost = f"{item.cost:,}" if item.cost else "—"
        if item.prompt == "options" and item.options:
            cost = " / ".join(f"{option['cost']:,}" for option in item.options)
        status = "Available" if allowed else reason
        if allowed and item.needs_gm:
            status = f"GM approved: {item.needs_gm}"
        for column, text in enumerate((item.name, item.current, item.next, cost, status)):
            cell = QTableWidgetItem(text)
            if column == 3:
                cell.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            if not allowed:
                cell.setForeground(QBrush(QColor("#8a8a8a")))
            self.table.setItem(row, column, cell)
        button = QPushButton("Buy")
        button.setEnabled(allowed)
        button.clicked.connect(lambda _=False, selected=item: self.buy(selected))
        self.table.setCellWidget(row, len(COLUMNS) - 1, button)

    def _show_details(self, row):
        if not 0 <= row < len(self._items):
            return
        item = self._items[row]
        lines = [f"<b>{item.name}</b> <i>({item.source})</i>"]
        if item.requirement:
            lines.append(f"<b>Requirement:</b> {item.requirement}")
        if item.blocked:
            lines.append(f"<b>Unavailable:</b> {item.blocked}")
        elif item.needs_gm:
            lines.append(f"<b>GM approval:</b> {item.needs_gm}")
        if item.description:
            lines.append(item.description)
        self.details_label.setText("<br>".join(lines))

    def _update_header(self):
        if self.shop is None:
            self.xp_label.setText("")
            return
        spent_here = sum(entry["cost"] - entry.get("refund", 0) for entry in self._session_entries())
        self.xp_label.setText(
            f"XP available: {self.shop.available_xp:,}"
            + (f"  (spent here: {spent_here:,})" if spent_here else "")
        )
        self.undo_button.setEnabled(bool(self._history))

    def _session_entries(self):
        log = self.character.get("xp_purchases") or []
        return log[len(log) - len(self._history):] if self._history else []

    # ---------------------------------------------------------
    # Buying
    # ---------------------------------------------------------
    def buy(self, item, choice=None):
        if self.shop is None:
            return None
        if choice is None and item.prompt:
            choice = self._ask_choice(item)
            if choice is None:
                return None
        before = snapshot(self.character)
        try:
            entry = self.shop.buy(item, self.gm_override.isChecked(), choice)
        except PurchaseError as error:
            QMessageBox.warning(self, "Can't Buy", str(error))
            return None
        self._history.append((before, entry["name"]))
        text = f"{entry['name']} - {entry['cost']:,} XP"
        if entry.get("refund"):
            text += f" (refunded {entry['refund']:,} XP of off-Connection Aspect costs)"
        self.history_list.addItem(text)
        self._refresh_items()
        return entry

    def _ask_choice(self, item):
        if item.prompt == "options":
            labels = [option["label"] for option in item.options]
            label, accepted = QInputDialog.getItem(
                self, item.prompt_label or item.name, item.requirement or item.name, labels, 0, False
            )
            if not accepted:
                return None
            return next(option["value"] for option in item.options if option["label"] == label)
        if item.suggestions:
            value, accepted = QInputDialog.getItem(
                self, item.name, item.prompt_label, item.suggestions, 0, True
            )
        else:
            value, accepted = QInputDialog.getText(self, item.name, item.prompt_label)
        value = value.strip() if accepted else ""
        return value or None

    def undo(self):
        if not self._history:
            return
        before, _ = self._history.pop()
        self.character.clear()
        self.character.update(before)
        self.history_list.takeItem(self.history_list.count() - 1)
        self._refresh_items()
