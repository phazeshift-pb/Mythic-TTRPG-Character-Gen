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


@pytest.fixture
def finish_dialogs(tmp_path, monkeypatch):
    """Answer the name prompt and write exports under tmp_path."""
    from PySide6.QtWidgets import QInputDialog, QMessageBox

    from src.ui.creator import character_files

    fake_module = tmp_path / "src" / "ui" / "creator" / "character_files.py"
    monkeypatch.setattr(character_files, "__file__", str(fake_module))
    monkeypatch.setattr(QMessageBox, "information", lambda *args: None)
    monkeypatch.setattr(QMessageBox, "critical", lambda *args: None)

    def answer(name, accepted=True):
        monkeypatch.setattr(
            QInputDialog, "getText", lambda *args, **kwargs: (name, accepted)
        )

    return answer, fake_module.parents[2] / "characters"


def test_finishing_character_returns_to_landing_page(window, finish_dialogs):
    answer, characters_directory = finish_dialogs
    answer("Noble Six")

    window.finish_and_name_character()

    assert (characters_directory / "Noble Six.json").exists()
    assert window.pages.currentWidget() is window.landing_page


def test_cancelling_name_prompt_stays_on_setup_home(window, finish_dialogs):
    answer, characters_directory = finish_dialogs
    answer("Noble Six", accepted=False)
    window.pages.setCurrentWidget(window.character_setup_home)

    window.finish_and_name_character()

    assert not characters_directory.exists()
    assert window.pages.currentWidget() is window.character_setup_home
    assert hasattr(window, "generated_character")


def test_failed_export_stays_on_setup_home(window, finish_dialogs, monkeypatch):
    answer, _ = finish_dialogs
    answer("Noble Six")
    window.pages.setCurrentWidget(window.character_setup_home)

    def fail_write(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", fail_write)

    window.finish_and_name_character()

    assert window.pages.currentWidget() is window.character_setup_home
    assert hasattr(window, "generated_character")


def _creator_state(ui):
    """Everything a player could see or inherit when opening the creator."""
    home = ui.character_setup_home
    combos = {
        "soldier": ui.soldier_combo,
        "human": ui.human_combo,
        "guardian": ui.guardian_combo,
        "upbringing": ui.upbringing_combo,
        "environment": ui.environment_combo,
        "subclass": ui.subclass_combo,
        "connection": ui.connection_combo,
        **{f"lifestyle{i}": combo for i, combo in enumerate(ui.lifestyle_combos)},
    }
    return {
        "xp": ui.experience_input.value(),
        "tier": ui.experience_tier_label.text(),
        "mode": ui.selected_mode,
        "mode_tiles": [
            tile.isChecked()
            for tile in ui.version_and_expansions_page.mode_tiles.values()
        ],
        "continue": ui.version_and_expansions_page.continue_button.isEnabled(),
        "home_buttons": [button.isEnabled() for button in home.home_buttons],
        "finish": home.finish_character_button.isEnabled(),
        "equipment_button": home.equipment_or_light_powers_button.text(),
        "combos": {
            name: (combo.currentText(), combo.count()) for name, combo in combos.items()
        },
        "setup_category": ui.initial_character_setup_page._selected_category,
        "setup_next": ui.generate_button.isEnabled(),
        "points_option": ui.creation_points_combo.currentIndex(),
        "allocations": ui._creation_allocations,
        "points_label": ui.creation_points_remaining_label.text(),
        "points_controls": len(ui.characteristic_value_labels),
        "points_grid": ui.characteristic_grid.count(),
        "points_next": ui.next_button.isEnabled(),
        "outliers": [tile.isChecked() for tile, _, _ in ui.outlier_tiles],
        "outlier_stats": ui._outlier_characteristics,
        "outlier_done": ui.outlier_done_button.text(),
        "luck": ui.outlier_page.available_luck_label.text(),
        "packs": [button.isChecked() for button, _ in ui.specialization_tiles],
        "packs_next": ui.specialization_done_button.isEnabled(),
        "packs_next_text": ui.specialization_done_button.text(),
        "equipment_title": ui.equipment_page_title.text(),
        "equipment_tiles": len(ui.equipment_tiles),
        "equipment_grid": ui.equipment_grid.count(),
        "equipment_done": ui.equipment_done_button.text(),
        "light_panel_hidden": ui.equipment_page.category_panel.isHidden(),
        "light_categories": [
            button.isChecked() for button in ui.equipment_page.category_buttons.values()
        ],
        "light_tiles": (len(ui.light_aspect_tiles), len(ui.light_ability_tiles)),
        "light_xp_label": ui.equipment_page.experience_remaining_label.text(),
        "light_options": (
            ui.equipment_page.options_title.text(),
            ui.equipment_page.options_description.text(),
        ),
        "light_selected": (
            ui._selected_light_category,
            ui._selected_light_aspects,
            ui._selected_light_powers,
            ui._selected_light_supers,
            ui._light_xp_spent,
        ),
        "soldier_skills": ui._selected_soldier_skills,
        "background_choices": ui._background_choices,
        "pack_choices": ui._equipment_pack_choices,
        "core_soldier": getattr(ui, "_selected_core_soldier", None),
        "character": hasattr(ui, "generated_character"),
        "pre_specialization": hasattr(ui, "_pre_specialization_skills"),
    }


def _pick(combo, index=1):
    combo.setCurrentIndex(index)


def _build_core_character(ui, monkeypatch):
    from src.ui.creator import equipment as equipment_module

    class PickFirst:
        def __init__(self, title, groups, selected=(), parent=None):
            self.selected_choices = [group["labels"][0] for group in groups]

        def exec(self):
            from PySide6.QtWidgets import QDialog

            return QDialog.DialogCode.Accepted

    monkeypatch.setattr(equipment_module, "BackgroundChoiceDialog", PickFirst)
    monkeypatch.setattr(ui, "_ensure_background_choices", lambda: True)
    monkeypatch.setattr(
        ui,
        "_choose_lifestyle_options",
        lambda record, roll, groups: [group["labels"][0] for group in groups],
    )
    ui.experience_input.setValue(100000)
    ui.version_and_expansions_page.mode_tiles["Core"].setChecked(True)
    ui.soldier_combo.setCurrentIndex(ui.soldier_combo.findData("marine"))
    _pick(ui.upbringing_combo)
    _pick(ui.environment_combo)
    for combo in ui.lifestyle_combos:
        _pick(combo)
    ui._background_choices["upbringing"] = {
        "name": ui.upbringing_combo.currentData(),
        "choices": ["stale"],
    }
    ui._refresh_initial_setup_options()
    ui.initial_character_setup_page.select_category("lifestyles")
    ui.generate_character()
    _allocate_all_points(ui)
    _select_outlier(ui, "Robust")
    ui.outlier_done_button.click()
    ui.specialization_tiles[0][0].setChecked(True)
    ui.specialization_done_button.click()
    next(b for b, name, _ in ui.equipment_tiles if name == "point_man").setChecked(True)
    ui.equipment_done_button.click()
    assert ui.character_setup_home.finish_character_button.isEnabled()


def _build_light_and_sky_character(ui, monkeypatch):
    ui.experience_input.setValue(1000000)
    ui.version_and_expansions_page.mode_tiles["Light & Sky"].setChecked(True)
    _pick(ui.human_combo)
    ui.guardian_combo.setCurrentIndex(ui.guardian_combo.findData("titan"))
    ui.subclass_combo.setCurrentIndex(0)
    _pick(ui.connection_combo)
    ui._refresh_initial_setup_options()
    ui.generate_character()
    _allocate_all_points(ui)
    ui.outlier_done_button.click()
    ui.specialization_tiles[0][0].setChecked(True)
    ui.specialization_done_button.click()
    ui.equipment_page.category_buttons["aspects"].click()
    ui.light_aspect_tiles[0][0].setChecked(True)
    ui.equipment_done_button.click()
    assert ui.character_setup_home.finish_character_button.isEnabled()


@pytest.fixture
def blank_window(qt_app, project_root):
    from src.ui.main_window import MainWindow

    ui = MainWindow()
    yield ui
    ui.close()


@pytest.mark.parametrize(
    "build", [_build_core_character, _build_light_and_sky_character]
)
def test_saving_character_resets_creator_to_new_window_state(
    blank_window, finish_dialogs, monkeypatch, build
):
    from src.ui.main_window import MainWindow

    answer, characters_directory = finish_dialogs
    answer("Noble Six")
    fresh = MainWindow()
    new_window_state = _creator_state(fresh)
    fresh.close()

    build(blank_window, monkeypatch)
    blank_window.character_setup_home.finish_character_button.click()

    assert (characters_directory / "Noble Six.json").exists()
    assert _creator_state(blank_window) == new_window_state


@pytest.mark.parametrize(
    "first", [_build_core_character, _build_light_and_sky_character]
)
def test_second_character_after_saving_starts_clean(
    blank_window, finish_dialogs, monkeypatch, first
):
    import json

    from PySide6.QtCore import QEvent
    from PySide6.QtWidgets import QApplication

    answer, characters_directory = finish_dialogs
    answer("First")
    first(blank_window, monkeypatch)
    blank_window.character_setup_home.finish_character_button.click()
    # The app's event loop would destroy the replaced tiles at this point.
    QApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)

    blank_window.create_character_button.click()
    assert blank_window.pages.currentWidget() is blank_window.character_setup_home

    _build_core_character(blank_window, monkeypatch)
    answer("Second")
    blank_window.character_setup_home.finish_character_button.click()

    saved = json.loads(
        (characters_directory / "Second.json").read_text(encoding="utf-8")
    )
    assert saved["ruleset"] == "Core"
    assert saved["character"]["name"] == "Second"
    assert saved["character"]["outliers"] == ["Robust"]
    assert saved["selections"]["equipment"]["pack"] == "point_man"
    assert sum(saved["selections"]["creation_points"]["allocations"].values()) == (
        saved["selections"]["creation_points"]["total"]
    )


def _start_light_and_sky_setup(ui, monkeypatch):
    ui.experience_input.setValue(1000000)
    ui.version_and_expansions_page.mode_tiles["Light & Sky"].setChecked(True)


@pytest.fixture
def discard_answers(monkeypatch):
    """Answer the discard prompt, recording each time it is asked."""
    from PySide6.QtWidgets import QMessageBox

    asked = []

    def answer(button):
        def question(*args):
            asked.append(args)
            return button

        monkeypatch.setattr(QMessageBox, "question", question)

    answer.asked = asked
    return answer


@pytest.mark.parametrize(
    "build",
    [_build_core_character, _build_light_and_sky_character, _start_light_and_sky_setup],
)
def test_discard_resets_creator_and_returns_to_landing_page(
    blank_window, discard_answers, monkeypatch, build
):
    from PySide6.QtWidgets import QMessageBox

    from src.ui.main_window import MainWindow

    fresh = MainWindow()
    new_window_state = _creator_state(fresh)
    fresh.close()
    discard_answers(QMessageBox.StandardButton.Yes)
    build(blank_window, monkeypatch)
    blank_window.pages.setCurrentWidget(blank_window.character_setup_home)

    blank_window.character_setup_home.discard_button.click()

    assert len(discard_answers.asked) == 1
    assert blank_window.pages.currentWidget() is blank_window.landing_page
    assert _creator_state(blank_window) == new_window_state


def test_declining_discard_keeps_the_character(
    blank_window, discard_answers, monkeypatch
):
    from PySide6.QtWidgets import QMessageBox

    discard_answers(QMessageBox.StandardButton.No)
    _build_core_character(blank_window, monkeypatch)
    blank_window.pages.setCurrentWidget(blank_window.character_setup_home)
    character = blank_window.generated_character

    blank_window.character_setup_home.discard_button.click()

    assert blank_window.pages.currentWidget() is blank_window.character_setup_home
    assert blank_window.generated_character is character
    assert blank_window.character_setup_home.finish_character_button.isEnabled()


def test_discard_is_available_and_skips_prompt_with_no_changes(
    blank_window, discard_answers
):
    from PySide6.QtWidgets import QMessageBox

    discard_answers(QMessageBox.StandardButton.No)
    blank_window.pages.setCurrentWidget(blank_window.character_setup_home)
    assert blank_window.character_setup_home.discard_button.isEnabled()

    blank_window.character_setup_home.discard_button.click()

    assert discard_answers.asked == []
    assert blank_window.pages.currentWidget() is blank_window.landing_page


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
