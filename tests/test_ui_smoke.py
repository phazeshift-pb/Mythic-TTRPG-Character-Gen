"""UI smoke tests.

Every UI module must compile. When PySide6 is installed, the main window and
character sheet are also built offscreen, which catches wiring errors such as
a missing attribute or a bad signal connection.
"""
import os
import py_compile
from pathlib import Path

import pytest

UI_DIR = Path(__file__).resolve().parent.parent / "src" / "ui"


@pytest.mark.parametrize("path", sorted(UI_DIR.rglob("*.py")), ids=lambda p: p.relative_to(UI_DIR).as_posix())
def test_ui_module_compiles(path):
    py_compile.compile(str(path), doraise=True)


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def test_main_window_builds_in_both_modes(qt_app):
    from src.ui.main_window import MainWindow

    window = MainWindow()
    for mode in ("Core", "Light & Sky"):
        window.version_and_expansions_page._select_mode(mode, True)
        assert window.selected_mode == mode
        assert window.game_data.errors == []
    window.close()


def test_background_choice_dialog(qt_app):
    from src.ui.background_choice_dialog import BackgroundChoiceDialog

    groups = [
        {"section": "bonuses", "labels": ["+5 Agility", "+5 Courage"]},
        {"section": "penalties", "labels": ["-5 Strength", "-5 Toughness"]},
    ]
    dialog = BackgroundChoiceDialog("City", groups, selected=["+5 Courage"])
    assert dialog.selected_choices == ["+5 Courage", "-5 Strength"]


def test_sheet_armor_toggle_updates_stats_live(qt_app):
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.models import starting_armor
    from src.models.equipment_packs import armor_index
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader().load_all()
    armors = armor_index(data)
    soldier = data.get("soldier_type", "spartan_iv")
    character = CharacterGenerator(data).generate("t", "spartan_iv", auto_assign_skills=False)
    character.apply_starting_armor(
        "GEN II Powered Armor", None, starting_armor.worn_bonus("GEN II Powered Armor", soldier, armors)
    )
    export = asdict(character)
    export.pop("debug_log")
    base_str = export["characteristics"]["STR"]

    sheet = InteractiveCharacterSheet()
    sheet.set_character(export, "Core", data)
    assert sheet.armor_equipped_checkbox.isChecked()
    assert sheet.characteristic_labels["STR"].text() == f"{base_str + 25} (+25)"
    worn_carry = sheet.carrying_capacity_labels["carry"].text()

    sheet.armor_equipped_checkbox.setChecked(False)
    assert sheet.characteristic_labels["STR"].text() == str(base_str)
    assert sheet.carrying_capacity_labels["carry"].text() != worn_carry
    assert sheet.character_data_for_save()["armor_equipped"] is False
    assert sheet.character_data_for_save()["characteristics"]["STR"] == base_str


def test_starting_armor_dialog(qt_app):
    from src.data_loader import DataLoader
    from src.models.equipment_packs import armor_index
    from src.ui.starting_armor_dialog import StartingArmorDialog

    data = DataLoader().load_all()
    armors = armor_index(data)
    soldier = data.get("soldier_type", "spartan_ii")
    dialog = StartingArmorDialog(soldier, armors, data, selected={
        "armor": "Mark VI Powered Assault Armor",
        "variant": {"name": "Recon", "generation": "GEN I"},
    })
    assert dialog.selected_armor == "Mark VI Powered Assault Armor"
    assert dialog.selected_variant["name"] == "Recon"
    dialog.armor_combo.setCurrentIndex(0)  # SPI Mark I takes no variants
    assert not dialog.variant_combo.isEnabled() and dialog.selected_variant is None


def _guardian_export(data):
    from dataclasses import asdict

    from src.generator.character_generator import CharacterGenerator

    subclass = next(iter(data.get("soldier_type", "titan")["subclasses"]))
    character = CharacterGenerator(data, use_light_and_sky=True).generate(
        "Guardian", "titan", subclass=subclass, human_soldier_type="exo",
        guardian_class="titan", auto_assign_skills=False,
    )
    export = asdict(character)
    export.pop("debug_log")
    return export


def test_loot_dialog_rolls_and_adds_to_sheet(qt_app):
    import random

    from src.data_loader import DataLoader
    from src.loot.generator import LootGenerator
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet
    from src.ui.loot_dialog import LootDialog

    data = DataLoader(use_light_and_sky=True).load_all()
    sheet = InteractiveCharacterSheet()
    sheet.set_character(_guardian_export(data), "Light & Sky", data)
    assert not sheet.loot_button.isHidden()
    base_agi = sheet.character_data["characteristics"]["AGI"]

    dialog = LootDialog(LootGenerator(data, random.Random(7)), on_add=sheet.add_loot, parent=sheet)
    dialog.rarity_combo.setCurrentIndex(dialog.rarity_combo.findData("Legendary"))
    dialog.generate()
    assert dialog.current_roll["kind"] == "weapon"
    assert "PERKS" in dialog.card_label.text()
    dialog.add_to_character()
    weapon = sheet.character_data_for_save()["weapons"][-1]
    assert weapon["source"] == "light_and_sky_loot"
    assert weapon["name"] in sheet.weapon_label.text()

    dialog.kind_combo.setCurrentIndex(dialog.kind_combo.findData("armor"))
    assert dialog.material_combo.isVisibleTo(dialog)
    dialog.generate()
    roll = dialog.current_roll
    assert roll["kind"] == "armor"
    sheet.add_loot(roll, confirm_replace=False)
    saved = sheet.character_data_for_save()
    assert saved["armor_loot"] == roll
    assert saved["armor"] in sheet.armor_label.text()
    expected = base_agi + roll["agility_modifier"]
    assert sheet.characteristic_labels["AGI"].text().startswith(str(max(0, expected)))
    dialog.close()

    sheet.set_character(saved, "Core", data)
    assert sheet.loot_button.isHidden()
