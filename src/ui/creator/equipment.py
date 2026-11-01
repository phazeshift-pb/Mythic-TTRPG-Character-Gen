# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Core equipment pack selection.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from PySide6.QtWidgets import QDialog, QLabel

from src.models.equipment_packs import (
    armory_index,
    choice_groups,
    describe,
    resolve_pack,
)
from src.ui.background_choice_dialog import BackgroundChoiceDialog


class EquipmentMixin:
    def _build_equipment_tiles(self):
        self.equipment_page.set_light_mode(False)
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

        self.equipment_tiles.clear()
        if self.selected_mode != "Core" or not hasattr(self, "game_data"):
            return

        soldier_name = getattr(self, "_selected_core_soldier", None)
        if not soldier_name:
            return
        soldier_data = self.game_data.get("soldier_type", soldier_name) or {}
        equipment_sets = soldier_data.get("equipment_sets", {})
        if not equipment_sets:
            self.equipment_grid.addWidget(
                QLabel("No equipment packs are available for this soldier type."),
                0, 0, 1, 3,
            )
            return

        for index, (pack_name, items) in enumerate(equipment_sets.items()):
            tile, select_button = self._create_selection_tile(
                pack_name.replace("_", " ").title(),
                "\n".join(describe(item) for item in items),
                min_height=145,
            )
            select_button.toggled.connect(
                lambda checked, selected_tile=select_button: self.select_equipment_tile(
                    selected_tile, checked
                )
            )
            self.equipment_tiles.append((select_button, pack_name, items))
            self.equipment_grid.addWidget(tile, index // 3, index % 3)

    def select_equipment_tile(self, selected_tile, checked):
        if checked:
            for button, _, _ in self.equipment_tiles:
                if button is not selected_tile:
                    button.setChecked(False)
        self.update_equipment_selection()

    def update_equipment_selection(self):
        selected = next(
            (pack_name for button, pack_name, _ in self.equipment_tiles if button.isChecked()),
            None,
        )
        self.equipment_done_button.setText(
            f"Done ({selected.replace('_', ' ').title()})" if selected else "Done"
        )

    def open_equipment_page(self):
        self.character_setup_home.set_character_ready_to_export(False)
        if self.selected_mode == "Light & Sky":
            self.equipment_page.set_light_mode(True)
            self._build_light_power_tiles()
            self.update_light_power_selection()
        else:
            self._build_equipment_tiles()
            self.update_equipment_selection()
        self.pages.setCurrentWidget(self.equipment_page)

    def finish_equipment_selection(self):
        if self.selected_mode == "Light & Sky":
            self.finish_light_power_selection()
            return

        if hasattr(self, "generated_character"):
            selected = next(
                (
                    (pack_name, items)
                    for tile, pack_name, items in self.equipment_tiles
                    if tile.isChecked()
                ),
                None,
            )
            choices = []
            if selected:
                choices = self._prompt_equipment_choices(*selected)
                if choices is None:
                    return  # player cancelled; stay on the equipment page
            self.generated_character.equipment = []
            self.generated_character.weapons = []
            self.generated_character.equipment_pack = None
            self._equipment_pack_choices = {}
            if selected:
                pack_name, items = selected
                weapons, gear, problems = resolve_pack(
                    items, choices, armory_index(self.game_data)
                )
                for problem in problems:
                    self.generated_character.log(f"Equipment pack: {problem}")
                self.generated_character.apply_equipment_pack(pack_name, gear, weapons)
                self._equipment_pack_choices = {"name": pack_name, "choices": choices}
        self.character_setup_home.set_character_ready_to_export(True)
        self.pages.setCurrentWidget(self.character_setup_home)

    def _prompt_equipment_choices(self, pack_name, items):
        """Pick one weapon for each either/or line. None if the player cancels."""
        groups = choice_groups(items)
        if not groups:
            return []
        stored = getattr(self, "_equipment_pack_choices", {}) or {}
        previous = stored.get("choices", []) if stored.get("name") == pack_name else []
        dialog = BackgroundChoiceDialog(
            pack_name.replace("_", " ").title(),
            groups,
            selected=previous,
            parent=self,
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        return dialog.selected_choices

    def _clear_equipment_grid(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
