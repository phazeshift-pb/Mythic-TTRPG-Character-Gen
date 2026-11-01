# pyright: reportAttributeAccessIssue=false, reportArgumentType=false
"""Core equipment pack selection.

Part of MainWindow (src/ui/main_window.py); methods use its widgets and state via self.
"""

from PySide6.QtWidgets import QDialog, QLabel

from src.models.equipment_packs import (
    armor_index,
    armory_index,
    choice_groups,
    describe,
    resolve_pack,
)
from src.models import starting_armor
from src.ui.background_choice_dialog import BackgroundChoiceDialog
from src.ui.starting_armor_dialog import StartingArmorDialog


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
            starting = self._prompt_starting_armor()
            if starting is None:
                return  # player cancelled; stay on the equipment page
            self.generated_character.equipment = []
            self.generated_character.weapons = []
            self.generated_character.armor = None
            self.generated_character.armor_variant = None
            self.generated_character.armor_bonus = {}
            self.generated_character.equipment_pack = None
            self._equipment_pack_choices = {}
            if selected:
                pack_name, items = selected
                contents = resolve_pack(
                    items,
                    choices,
                    armory_index(self.game_data),
                    armor_index(self.game_data),
                )
                for problem in contents.problems:
                    self.generated_character.log(f"Equipment pack: {problem}")
                self.generated_character.apply_equipment_pack(
                    pack_name, contents.equipment, contents.weapons, contents.armor
                )
                self._equipment_pack_choices = {"name": pack_name, "choices": choices}
            if starting:
                self.generated_character.apply_starting_armor(
                    starting["armor"], starting.get("variant"), starting.get("bonus")
                )
                self._equipment_pack_choices["starting_armor"] = {
                    "armor": starting["armor"],
                    "variant": starting.get("variant"),
                }
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

    def _current_soldier_data(self):
        name = getattr(self, "_selected_core_soldier", None)
        return self.game_data.get("soldier_type", name) if name else None

    def _prompt_starting_armor(self):
        """Spartan suit and variant pick.

        Returns {} when the soldier type has no starting-armor choice, None if
        the player cancels, else {"armor", "variant", "bonus"}.
        """
        soldier_data = self._current_soldier_data()
        if not starting_armor.armor_options(soldier_data):
            return {}
        armors = armor_index(self.game_data)
        stored = (getattr(self, "_equipment_pack_choices", {}) or {}).get("starting_armor")
        dialog = StartingArmorDialog(
            soldier_data, armors, self.game_data, selected=stored, parent=self
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return None
        armor = dialog.selected_armor
        variant = starting_armor.variant_entry(dialog.selected_variant)
        for problem in starting_armor.validate_choice(
            soldier_data, armor, variant, armors, self.game_data
        ):
            self.generated_character.log(f"Starting armor: {problem}")
        return {
            "armor": armor,
            "variant": variant,
            "bonus": starting_armor.worn_bonus(armor, soldier_data, armors),
        }

    def _clear_equipment_grid(self):
        while self.equipment_grid.count():
            item = self.equipment_grid.takeAt(0)
            if item is None:
                continue
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
