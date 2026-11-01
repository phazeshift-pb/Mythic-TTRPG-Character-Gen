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
