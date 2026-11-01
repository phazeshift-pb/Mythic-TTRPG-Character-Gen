"""Regression tests for state that must survive the character creation flow."""
import os
from pathlib import Path

import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator

ROOT = Path(__file__).resolve().parent.parent
FORTE = {"name": "Forte", "effect": "+1 Mythic."}


@pytest.fixture(autouse=True)
def project_root(monkeypatch):
    # DataLoader reads data/ relative to the working directory.
    monkeypatch.chdir(ROOT)


@pytest.fixture(scope="module")
def qt_app():
    pytest.importorskip("PySide6")
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(qt_app, project_root):
    from src.ui.main_window import MainWindow

    ui = MainWindow()
    ui.version_and_expansions_page._select_mode("Core", True)
    ui.soldier_combo.clear()
    ui.soldier_combo.addItem("Marine", "marine")
    ui.soldier_combo.setCurrentIndex(0)
    ui.generate_character()
    yield ui
    ui.close()


def _allocate_all_points(ui):
    total = ui.creation_points_combo.currentData()
    codes = list(ui._creation_allocations)
    while sum(ui._creation_allocations.values()) < total:
        for code in codes:
            if sum(ui._creation_allocations.values()) < total:
                ui.adjust_creation_points(code, 1)


def _select_outlier(ui, name):
    for tile, outlier, _ in ui.outlier_tiles:
        tile.setChecked(outlier.get("name") == name)


def test_outlier_page_keeps_allocated_points(window):
    _allocate_all_points(window)
    allocated = dict(window.generated_character.characteristics)

    window.outlier_done_button.click()

    assert window.generated_character.characteristics == allocated


def test_export_includes_allocated_points_in_stats_and_wounds(window):
    _allocate_all_points(window)
    allocated = dict(window.generated_character.characteristics)

    window.outlier_done_button.click()
    character = window._character_export_data()["character"]

    assert character["characteristics"] == allocated
    assert character["wounds"] == 40 + (allocated["TOU"] // 10) * 2


def test_outlier_page_can_be_finished_repeatedly(window):
    _allocate_all_points(window)
    allocated = dict(window.generated_character.characteristics)
    character = window.generated_character

    _select_outlier(window, "Robust")
    window.outlier_done_button.click()
    assert character.outliers == ["Robust"]
    assert character.characteristics == allocated

    _select_outlier(window, None)
    window.outlier_done_button.click()
    assert character.outliers == []
    assert character.characteristics == allocated


def test_equipment_pack_links_armory_weapons(window, monkeypatch):
    from src.ui.creator import equipment as equipment_module

    class PickFirst:
        def __init__(self, title, groups, selected=(), parent=None):
            self.selected_choices = [group["labels"][0] for group in groups]

        def exec(self):
            from PySide6.QtWidgets import QDialog

            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(equipment_module, "BackgroundChoiceDialog", PickFirst)
    window.open_equipment_page()
    tile = next(button for button, name, _ in window.equipment_tiles if name == "point_man")
    tile.setChecked(True)
    window.equipment_done_button.click()

    character = window.generated_character
    names = [weapon["name"] for weapon in character.weapons]
    assert names[0] == "MA5B Individual Combat Weapon System"
    assert "M9 High-Explosive Dual-Purpose Grenade" in names
    assert "Flashlight" in character.equipment
    assert character.armor == "M50B Standard"
    assert not any("Grenade" in item for item in character.equipment)
    export = window._character_export_data()
    assert export["selections"]["equipment"]["pack"] == "point_man"
    assert len(export["selections"]["equipment"]["choices"]) == 4


def test_spartan_picks_mjolnir_and_variant(qt_app, project_root, monkeypatch):
    from PySide6.QtWidgets import QDialog

    from src.ui.creator import equipment as equipment_module
    from src.ui.main_window import MainWindow

    class PickFirst:
        def __init__(self, title, groups, selected=(), parent=None):
            self.selected_choices = [group["labels"][0] for group in groups]

        def exec(self):
            return QDialog.DialogCode.Accepted

    class PickGen2Recon:
        def __init__(self, soldier_data, armors, game_data, selected=None, parent=None):
            from src.models import starting_armor

            self.selected_armor = "GEN II Powered Armor"
            self.selected_variant = starting_armor.find_variant(game_data, "GEN II", "Recon")

        def exec(self):
            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(equipment_module, "BackgroundChoiceDialog", PickFirst)
    monkeypatch.setattr(equipment_module, "StartingArmorDialog", PickGen2Recon)
    ui = MainWindow()
    ui.version_and_expansions_page._select_mode("Core", True)
    ui.soldier_combo.clear()
    ui.soldier_combo.addItem("Spartan IV", "spartan_iv")
    ui.soldier_combo.setCurrentIndex(0)
    ui.generate_character()
    ui.open_equipment_page()
    tile = next(button for button, name, _ in ui.equipment_tiles if name == "point_man")
    tile.setChecked(True)
    ui.equipment_done_button.click()

    character = ui.generated_character
    assert character.armor == "GEN II Powered Armor"
    assert character.armor_variant["name"] == "Recon"
    assert character.armor_bonus["TOU"] == 5  # Spartan IV GEN II bonus
    assert character.weapons and character.weapons[0]["name"] == "MA5K Carbine"
    export = ui._character_export_data()["selections"]["equipment"]
    assert export["starting_armor"]["variant"]["name"] == "Recon"
    ui.close()


def test_core_forte_does_not_change_game_data():
    data = DataLoader(use_light_and_sky=False).load_all()
    generator = CharacterGenerator(data)

    for _ in range(2):
        character = generator.generate("t", "air_force", auto_assign_skills=False)
        assert character.mythic_characteristics == {}
        character.apply_outlier(FORTE, 0, "TOU")

    assert data.get("soldier_type", "air_force")["mythic_characteristics"] == {}


def test_guardian_mythics_do_not_change_human_record():
    data = DataLoader(use_light_and_sky=True).load_all()
    generator = CharacterGenerator(data, use_light_and_sky=True)
    subclass = next(iter(data.get("soldier_type", "titan")["subclasses"]))

    guardian = generator.generate(
        "t",
        "titan",
        subclass=subclass,
        human_soldier_type="exo",
        guardian_class="titan",
        auto_assign_skills=False,
    )

    assert guardian.mythic_characteristics == {"STR": "+3", "TOU": "+4", "AGI": "+1"}
    assert data.get("soldier_type", "exo")["mythic_characteristics"] == {}


@pytest.mark.parametrize(
    "soldier, expected",
    [
        # Marine: +5 Simple STR/AGI/PER, +10 Rookie WFR on a 25 base.
        ("marine", {"STR": 30, "AGI": 30, "WFR": 35, "PER": 30, "TOU": 25}),
        # ORION: base 35/40/35/25..., +5 WFM, +10 WFR, +5 PER, +5 LDR.
        ("orion", {"WFM": 30, "WFR": 35, "PER": 45, "LDR": 30, "STR": 35}),
        # Navy: +10 Rookie INT and PER.
        ("navy_technician", {"INT": 35, "PER": 35, "STR": 25}),
    ],
)
def test_soldier_type_advancements_apply_to_characteristics(soldier, expected):
    data = DataLoader().load_all()
    character = CharacterGenerator(data).generate(
        "t", soldier, starting_experience=10000, auto_assign_skills=False
    )
    for code, value in expected.items():
        assert character.characteristics[code] == value, code
    assert any("Soldier Type advancement" in line for line in character.debug_log)


def test_soldier_type_advancements_count_as_owned_in_xp_shop():
    from dataclasses import asdict

    from src.models.xp_shop import XpShop

    data = DataLoader().load_all()
    character = asdict(
        CharacterGenerator(data).generate(
            "t", "marine", starting_experience=10000, auto_assign_skills=False
        )
    )
    shop = XpShop(character, data, "Core")
    warfare_range = shop.find("characteristic:WFR")
    assert warfare_range.current.startswith("35 (Rookie)")
    assert warfare_range.cost == 800  # Intermediate is next
