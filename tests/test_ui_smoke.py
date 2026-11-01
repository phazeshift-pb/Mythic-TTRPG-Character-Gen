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


def test_xp_shop_page_buy_undo_and_apply(qt_app):
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.ui.main_window import MainWindow

    data = DataLoader().load_all()
    character = asdict(
        CharacterGenerator(data).generate(
            "t", "marine", starting_experience=6000, auto_assign_skills=False
        )
    )
    character.pop("debug_log")

    window = MainWindow()
    window.character_sheet.set_character(character, "Core", data)
    window.open_xp_shop()
    page = window.xp_shop_page
    assert window.pages.currentWidget() is page
    assert page.shop.categories()[0] == "Characteristics"
    assert "Connections" not in page.shop.categories()

    xp = page.shop.available_xp
    toughness = page.shop.find("characteristic:TOU")
    page.buy(toughness)
    assert page.shop.available_xp == xp - toughness.cost
    page.undo()
    assert page.shop.available_xp == xp

    page.buy(page.shop.find("skill:Appeal"))
    page.applied.emit(page.character)
    assert window.pages.currentWidget() is window.character_sheet
    assert window.character_sheet.character_data["skills"]["Appeal"] == 0
    assert window.character_sheet.character_data["experience"] == xp - 200
    window.close()


def test_sheet_shows_throwing_distance(qt_app):
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.models import throwing
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader().load_all()
    export = asdict(CharacterGenerator(data).generate("t", "marine", auto_assign_skills=False))
    export.pop("debug_log")
    export["weapons"] = [{"name": "M9 High-Explosive Dual-Purpose Grenade", "quantity": 1}]

    sheet = InteractiveCharacterSheet()
    sheet.set_character(export, "Core", data)
    stats = sheet._throwing_character
    strength = stats["characteristics"]["STR"]
    mythic = stats["mythic_characteristics"].get("STR", 0)

    best = throwing.throw_distance(strength, mythic)
    assert sheet.throw_max_label.text() == f"Max {best.range_text()}"
    assert sheet.throw_table.rowCount() == 1
    grenade = throwing.throw_distance(strength, mythic, 0.4, carry_weight=sheet._carry_weight)
    assert sheet.throw_table.item(0, 2).text() == grenade.range_text()

    sheet.throw_dof_input.setValue(2)
    worse = throwing.throw_distance(
        strength, mythic, 0.4, degrees_of_failure=2, carry_weight=sheet._carry_weight
    )
    assert sheet.throw_table.item(0, 2).text() == worse.range_text()


def test_sheet_attack_calculator(qt_app):
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader().load_all()
    export = asdict(CharacterGenerator(data).generate("t", "marine", auto_assign_skills=False))
    export.pop("debug_log")
    export["weapons"] = [
        {"name": "M6A Personal Defense Weapon System", "quantity": 1},
        {"name": "M1 Combat Knife", "quantity": 1},
        {"name": "AIE-486H Heavy Machine Gun", "quantity": 1},
    ]
    sheet = InteractiveCharacterSheet()
    sheet.set_character(export, "Core", data)
    stats = sheet._throwing_character["characteristics"]
    weapon = sheet.attack_weapon_input

    weapon.setCurrentIndex(weapon.findText("M6A Personal Defense Weapon System"))
    assert sheet.attack_mode_input.currentData() == "fire"
    assert sheet.attack_fire_mode_input.currentData() == "Semi-Auto (2)"
    assert sheet.attack_total_label.text() == f"Roll {stats['WFR'] + 10} or under"

    sheet.attack_called_shot_input.setChecked(True)
    assert sheet.attack_total_label.text() == f"Roll {stats['WFR'] + 10 - 30} or under"
    sheet.attack_called_shot_input.setChecked(False)

    weapon.setCurrentIndex(weapon.findText("M1 Combat Knife"))
    assert sheet.attack_mode_input.currentData() == "melee"
    assert "Warfare Melee" in sheet.attack_base_label.text()

    weapon.setCurrentIndex(weapon.findText("AIE-486H Heavy Machine Gun"))
    assert "Heavy Weapon not Braced" in sheet.attack_breakdown_label.text()
    sheet.attack_braced_input.setChecked(True)
    assert "Heavy Weapon not Braced" not in sheet.attack_breakdown_label.text()
    assert "attack" not in "".join(sheet.character_data_for_save())
