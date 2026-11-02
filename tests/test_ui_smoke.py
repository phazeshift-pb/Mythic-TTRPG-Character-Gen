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
    # Start bare: these tests add their own loot (starting engrams are tested elsewhere)
    export.update(weapons=[], armor=None, armor_bonus={}, armor_loot=None)
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


def test_sheet_damage_resistance(qt_app):
    import random
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.loot.generator import LootGenerator
    from src.models import damage_resistance
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader(use_light_and_sky=True).load_all()
    sheet = InteractiveCharacterSheet()
    sheet.set_character(_guardian_export(data), "Light & Sky", data)
    roll = LootGenerator(data, random.Random(5)).generate_armor()
    sheet.add_loot(roll, confirm_replace=False)

    stats = sheet._throwing_character
    base = damage_resistance.damage_resistance(
        stats["characteristics"]["TOU"], stats["mythic_characteristics"].get("TOU", 0)
    )["chest"]["total"]
    assert sheet.dr_labels["chest"]["total"].text() == str(base + roll["armor_values"]["chest"])

    sheet.dr_other_inputs["chest"].setValue(3)
    assert sheet.dr_labels["chest"]["total"].text() == str(base + roll["armor_values"]["chest"] + 3)
    saved = sheet.character_data_for_save()
    assert saved["damage_resistance_other"] == {"chest": 3}

    sheet.armor_equipped_checkbox.setChecked(False)
    assert sheet.dr_labels["chest"]["total"].text() == str(base + 3)


def test_sheet_energy_shields(qt_app):
    import random

    from src.data_loader import DataLoader
    from src.loot.generator import LootGenerator
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader(use_light_and_sky=True).load_all()
    sheet = InteractiveCharacterSheet()
    sheet.set_character(_guardian_export(data), "Light & Sky", data)
    assert sheet.shield_labels["integrity"].text() == "—"
    assert not sheet.shield_current_input.isEnabled()

    sheet.add_loot(LootGenerator(data, random.Random(5)).generate_armor(), confirm_replace=False)
    assert [sheet.shield_labels[k].text() for k in ("integrity", "delay", "recharge")] == ["125", "5", "50"]
    assert sheet.shield_current_input.value() == 125

    sheet.shield_current_input.setValue(20)
    sheet.shield_recharge_button.click()
    sheet._recharge_energy_shield()
    assert sheet.shield_current_input.value() in (70, 120)
    saved = sheet.character_data_for_save()
    assert saved["energy_shield_current"] == sheet.shield_current_input.value()

    sheet.armor_equipped_checkbox.setChecked(False)
    assert sheet.shield_labels["integrity"].text() == "—"
    assert "energy_shield_current" not in sheet.character_data_for_save()


def test_skill_test_dialog_rolls(qt_app):
    import random

    from src.ui.skill_test_dialog import SkillTestDialog

    dialog = SkillTestDialog(
        "Athletics", [("Strength", "STR", 50)], 10, [("Challenging", 0), ("Hard", -20)],
        rng=random.Random(7),
    )
    result = dialog.roll()
    assert result.target == 60
    assert result.degrees_text in dialog.roll_result_label.text()
    assert dialog.roll_button.text() == "Roll Again"


def test_attack_roll_dialog(qt_app):
    import random
    from dataclasses import asdict

    from src.data_loader import DataLoader
    from src.generator.character_generator import CharacterGenerator
    from src.models import attack
    from src.ui.attack_roll_dialog import describe_hit, plan_attacks
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet
    from src.models import dice

    data = DataLoader().load_all()
    export = asdict(CharacterGenerator(data).generate("t", "marine", auto_assign_skills=False))
    export.pop("debug_log")
    export["weapons"] = [{"name": "M6A Personal Defense Weapon System", "quantity": 1}]
    sheet = InteractiveCharacterSheet()
    sheet.dice_rng = random.Random(3)
    sheet.set_character(export, "Core", data)
    weapon = sheet.attack_weapon_input
    weapon.setCurrentIndex(weapon.findText("M6A Personal Defense Weapon System"))
    sheet.attack_aim_input.setCurrentIndex(sheet.attack_aim_input.findData("full"))

    dialog = sheet.attack_roll_dialog()
    assert dialog.table.rowCount() == 1
    dialog.count_input.setValue(3)
    targets = [int(dialog.table.item(row, 1).text()) for row in range(3)]
    assert targets[0] == targets[1] == dialog.result.total
    assert targets[2] == dialog.result.total - 10  # Full Aim only helps the first two

    result = attack.AttackResult("WFR", 50, [("Called Shot: Body location", -30)], [])
    assert plan_attacks(result, 2) == [20, 20]
    # Missed the Called Shot but would have hit with 2 Degrees of Success without it
    assert "still hits" in describe_hit(dice.resolve_test(25, 20), 20, -30)
    assert describe_hit(dice.resolve_test(45, 20), 20, -30) == "Miss"
    assert describe_hit(dice.resolve_test(1, 20), 20, -30).startswith("You choose")


def _marine_sheet(data):
    from dataclasses import asdict

    from src.generator.character_generator import CharacterGenerator
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    export = asdict(CharacterGenerator(data).generate("t", "marine", auto_assign_skills=False))
    export.pop("debug_log")
    sheet = InteractiveCharacterSheet()
    sheet.set_character(export, "Core", data)
    return sheet, export


def test_sheet_skill_rows_show_training_and_open_a_test(qt_app, monkeypatch):
    from PySide6.QtWidgets import QFrame

    from src.data_loader import DataLoader
    from src.ui import interactive_character_sheet as sheet_module

    data = DataLoader().load_all()
    sheet, export = _marine_sheet(data)
    export["skills"] = {"Athletics": 10, "Appeal": 0}
    sheet.set_character(export, "Core", data)

    def pips(name):
        return [
            frame.property("role") == "pip-on"
            for frame in sheet.skill_rows[name].findChildren(QFrame)
            if str(frame.property("role")).startswith("pip-")
        ]

    assert pips("Athletics") == [True, True, False]
    assert pips("Appeal") == [True, False, False]
    assert pips("Command") == [False, False, False]
    assert sheet.skill_list.count() == len(sheet.skill_rows)

    opened = []

    class FakeDialog:
        def __init__(self, skill, characteristics, level, difficulties, parent=None, rng=None):
            opened.append((skill, level))

        def exec(self):
            pass

    monkeypatch.setattr(sheet_module, "SkillTestDialog", FakeDialog)
    sheet.skill_rows["Athletics"].click()
    sheet.skill_rows["Command"].click()
    assert opened == [("Athletics", 10), ("Command", -10)]

    # Reloading replaces the rows rather than adding to them.
    row_count = sheet.skill_list.count()
    sheet.set_character(export, "Core", data)
    assert sheet.skill_list.count() == row_count


def test_sheet_tabs_keep_notes_and_gear_text(qt_app):
    from src.data_loader import DataLoader

    data = DataLoader().load_all()
    sheet, export = _marine_sheet(data)
    export["medical_notes"] = "Broken rib"
    export["combat_notes"] = "Spare mags"
    export["equipment_pack"] = "point_man"
    export["weapons"] = [{"name": "M1 Combat Knife", "quantity": 1}]
    sheet.set_character(export, "Core", data)

    tabs = [sheet.tabs.tabText(index) for index in range(sheet.tabs.count())]
    assert tabs == ["Character", "Combat", "Notes"]
    for note in sheet.note_fields.values():
        assert sheet.notes_tab.isAncestorOf(note)
    assert sheet.combat_tab.isAncestorOf(sheet.throw_table)
    saved = sheet.character_data_for_save()
    assert saved["medical_notes"] == "Broken rib"
    assert saved["combat_notes"] == "Spare mags"
    assert sheet.equipment_pack_label.text() == "Point Man"
    assert "<b>M1 Combat Knife</b>" in sheet.weapon_label.text()
    assert saved["equipment_pack"] == "point_man"


def test_sheet_summary_text_is_escaped_and_handles_nothing(qt_app):
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet as Sheet

    assert Sheet._summary_html([]) == "None"
    text = Sheet._summary_html(["<Blade> - 1D10, Pierce 2\n    Perks: Sharp"])
    assert "<b>&lt;Blade&gt;</b>" in text
    assert "1D10, Pierce 2" in text
    assert "Perks: Sharp" in text


def test_sheet_style_does_not_reach_its_dialogs(qt_app):
    """The sheet's paper styling must stay off dialogs parented to the sheet."""
    from PySide6.QtWidgets import QDialog

    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    sheet = InteractiveCharacterSheet()
    dialog = QDialog(sheet)
    assert sheet.tabs.styleSheet() == ""
    assert sheet.tabs.parent().styleSheet() != ""  # the styled page holds the tabs
    assert sheet.styleSheet() == ""  # ...but the dialog's parent isn't styled
    assert dialog.styleSheet() == ""
    assert not sheet.tabs.parent().isAncestorOf(dialog)


def test_sheet_spin_box_buttons_receive_clicks(qt_app):
    """Both buttons must be clickable in every Qt style, not covered by the text field."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest
    from PySide6.QtWidgets import (
        QDoubleSpinBox, QSpinBox, QStyle, QStyleFactory, QStyleOptionSpinBox, QVBoxLayout, QWidget,
    )

    from src.ui import theme

    def click(page, box, control):
        option = QStyleOptionSpinBox()
        box.initStyleOption(option)
        rect = box.style().subControlRect(QStyle.ComplexControl.CC_SpinBox, option, control, box)
        # Through the window, so the click reaches whichever child is on top like a real one.
        QTest.mouseClick(
            page.windowHandle(), Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
            box.mapTo(page, rect.center()),
        )

    original_style = qt_app.style().objectName()
    try:
        for style_name in QStyleFactory.keys():
            qt_app.setStyle(style_name)
            page = QWidget()
            page.setStyleSheet(theme.SHEET_STYLE)
            layout = QVBoxLayout(page)
            vital = QSpinBox()
            vital.setProperty("role", "vital")
            boxes = [QSpinBox(), QDoubleSpinBox(), vital]
            for box in boxes:
                box.setRange(0, 100)
                layout.addWidget(box)
            page.show()
            QTest.qWaitForWindowExposed(page)
            for box in boxes:
                box.setValue(50)
                click(page, box, QStyle.SubControl.SC_SpinBoxUp)
                assert box.value() == 51, style_name
                click(page, box, QStyle.SubControl.SC_SpinBoxDown)
                assert box.value() == 50, style_name
            page.close()
    finally:
        qt_app.setStyle(original_style)


def test_light_and_sky_tab_slots_and_energy(qt_app):
    from src.data_loader import DataLoader
    from src.ui.interactive_character_sheet import InteractiveCharacterSheet

    data = DataLoader(use_light_and_sky=True).load_all()
    sheet = InteractiveCharacterSheet()
    export = _guardian_export(data)
    sheet.set_character(export, "Light & Sky", data)
    tabs = [sheet.tabs.tabText(index) for index in range(sheet.tabs.count())]
    assert tabs == ["Character", "Combat", "Light && Sky", "Notes"]
    page = sheet.light_page
    assert sheet.light_tab.isAncestorOf(page)

    # every possible slot is drawn; unbought ones are locked
    assert len(page.slot_tiles["aspect"]) == 4
    assert [tile.property("role") for tile in page.slot_tiles["aspect"][1:]] == ["slot-locked"] * 3
    assert len(page.slot_tiles["ability"]) == 5
    assert len(page.slot_tiles["super"]) == 1

    # energy starts full and is saved with the character
    assert page.energy_inputs["light"].value() == 100
    page._adjust_energy("light", -10)
    page.regen_buttons["New Turn"].click()
    saved = sheet.character_data_for_save()
    assert saved["light_energy"] == 95 and saved["super_energy"] == 100
    assert isinstance(saved["light_loadout"], dict)

    # a Core character has no Light & Sky tab
    core = DataLoader().load_all()
    _, marine = _marine_sheet(core)
    sheet.set_character(marine, "Core", core)
    assert sheet.tabs.indexOf(sheet.light_tab) == -1
