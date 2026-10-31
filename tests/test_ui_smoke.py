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
