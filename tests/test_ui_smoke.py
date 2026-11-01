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
