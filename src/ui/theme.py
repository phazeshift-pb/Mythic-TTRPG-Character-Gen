"""Shared colours and Qt stylesheets for the creator and character sheet.

Change a colour here and every page that uses these styles follows.
Page-specific one-off styles can stay inline next to their widget.
"""

from pathlib import Path

# Stylesheet url() paths resolve against the working directory unless absolute
UI_ICONS = (Path(__file__).resolve().parents[2] / "assets" / "ui").as_posix()

# Palette
BACKGROUND = "#242424"
TEXT = "#f2f0e6"
TEXT_MUTED = "#d5d2c6"
WHITE = "#ffffff"
GREEN = "#526b28"
GREEN_LIGHT = "#788f3e"
GREEN_DARK = "#35451d"
HIGHLIGHT = "#f7d36b"

# Headings
APP_TITLE = "font-size: 28px; font-weight: bold;"
PAGE_TITLE = (
    "font-size: 24px; font-weight: bold; padding: 10px; "
    f"border-bottom: 2px solid {GREEN};"
)
SECTION_HEADING = "font-size: 18px; font-weight: bold;"
SUBHEADING = "font-size: 16px; font-weight: bold; padding: 4px;"

# Panels and selection tiles
PANEL_BACKGROUND = f"background-color: {BACKGROUND};"
TILE_FRAME = (
    f"QFrame {{ background-color: {BACKGROUND}; border: 2px solid {GREEN}; "
    "border-radius: 8px; }"
)
TILE_TITLE = f"color: {TEXT}; font-weight: bold; font-size: 14px;"
TILE_TEXT = f"color: {TEXT_MUTED}; border: none; padding: 4px 8px 8px 8px;"

# Buttons
CATEGORY_BUTTON = (
    "QPushButton {"
    " text-align: left;"
    f" background-color: {BACKGROUND};"
    f" color: {TEXT};"
    f" border: 2px solid {GREEN};"
    " border-radius: 6px;"
    " padding: 8px;"
    " font-weight: bold;"
    "}"
    f"QPushButton:hover {{ border-color: {HIGHLIGHT}; }}"
    "QPushButton:checked {"
    f" background-color: {GREEN_DARK};"
    f" border: 3px solid {HIGHLIGHT};"
    "}"
)
SELECT_BUTTON = (
    "QPushButton {"
    " text-align: left;"
    f" background-color: {GREEN};"
    f" color: {WHITE};"
    f" border: 2px solid {GREEN_LIGHT};"
    " border-radius: 6px;"
    " padding: 14px;"
    " font-size: 16px;"
    " font-weight: bold;"
    "}"
    "QPushButton:hover {"
    f" background-color: {GREEN_LIGHT};"
    f" border-color: {HIGHLIGHT};"
    "}"
    "QPushButton:checked {"
    f" background-color: {GREEN_DARK};"
    f" border: 3px solid {HIGHLIGHT};"
    "}"
    "QPushButton:pressed {"
    f" background-color: {GREEN_DARK};"
    f" border-color: {HIGHLIGHT};"
    "}"
)
HOME_MENU_BUTTON = (
    "QPushButton { font-size: 18px; font-weight: bold; padding: 12px; }"
    f"QPushButton:hover {{ border: 2px solid {HIGHLIGHT}; }}"
)

# Character sheet: the creator's dark olive and gold, on near-black.
SHEET_SURFACE = "#1f201c"
SHEET_SURFACE_DEEP = "#30322a"
SHEET_FIELD = "#2a2b25"
SHEET_TEXT = TEXT
SHEET_TEXT_MUTED = "#b4b2a3"
SHEET_LINE = "#5a5c4e"
SHEET_DRAB = "#2c361c"
SHEET_DRAB_LIGHT = GREEN
SHEET_DRAB_TEXT = "#c9cdb0"
SHEET_DRAB_DISABLED = "#7d8568"
SHEET_HEADING = "#b9cb7d"
SHEET_RULE = GREEN_LIGHT
SHEET_ACCENT = HIGHLIGHT
SHEET_GOOD = "#a6d16a"
SHEET_BAD = "#f0907a"
SHEET_HEADING_FONT = '"Bahnschrift", "Segoe UI"'
# Light & Sky page: the two energy pools
SHEET_LIGHT_ENERGY = HIGHLIGHT
SHEET_SUPER_ENERGY = "#8fc6e8"

SHEET_ABILITY = (
    f"QLabel {{ color: {SHEET_TEXT}; padding: 1px 0; }}"
    f"QLabel:hover {{ color: {SHEET_ACCENT}; }}"
)

SHEET_STYLE = f"""
* {{ font-family: "Segoe UI"; font-size: 13px; color: {SHEET_TEXT}; }}
QToolTip {{
    background-color: {SHEET_SURFACE_DEEP}; color: {SHEET_TEXT};
    border: 1px solid {SHEET_LINE}; padding: 4px;
}}
#sheetPage {{ background-color: {SHEET_DRAB}; }}
#sheetMasthead {{ background-color: {SHEET_DRAB}; }}
#sheetMasthead QLabel {{ color: {SHEET_TEXT}; }}
#sheetMasthead QLabel[role="caption"] {{ color: {SHEET_DRAB_TEXT}; }}
#sheetMasthead QPushButton {{
    background-color: transparent; border: 1px solid {SHEET_DRAB_TEXT}; color: {SHEET_TEXT};
}}
#sheetMasthead QPushButton:hover {{ background-color: {SHEET_DRAB_LIGHT}; }}
#sheetMasthead QPushButton:disabled {{ border-color: {SHEET_DRAB_DISABLED}; color: {SHEET_DRAB_DISABLED}; }}
#sheetMasthead QPushButton[role="primary"] {{
    background-color: {SHEET_ACCENT}; color: {SHEET_SURFACE}; border-color: {SHEET_ACCENT};
}}
#sheetMasthead QPushButton[role="primary"]:hover {{ background-color: {SHEET_TEXT}; border-color: {SHEET_TEXT}; }}

QLabel[role="sheet-name"] {{
    font-family: {SHEET_HEADING_FONT}; font-size: 30px; font-weight: bold;
}}
QLabel[role="sheet-subtitle"] {{ font-size: 13px; }}
QLabel[role="xp-value"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 18px; font-weight: bold; }}

QTabWidget::pane {{ border: none; background-color: {SHEET_SURFACE}; }}
QTabBar {{ background-color: {SHEET_DRAB}; }}
QTabBar::tab {{
    background-color: {SHEET_DRAB_LIGHT}; color: {SHEET_TEXT};
    padding: 7px 22px; margin-right: 2px; margin-left: 0;
    font-family: {SHEET_HEADING_FONT}; font-weight: bold;
}}
QTabBar::tab:hover {{ background-color: {GREEN_DARK}; color: {SHEET_TEXT}; }}
QTabBar::tab:selected {{ background-color: {SHEET_SURFACE}; color: {SHEET_HEADING}; }}

QScrollArea {{ border: none; background-color: {SHEET_SURFACE}; }}
#sheetBody {{ background-color: {SHEET_SURFACE}; }}
QScrollBar:vertical {{ background: {SHEET_SURFACE_DEEP}; width: 10px; margin: 0; }}
QScrollBar:horizontal {{ background: {SHEET_SURFACE_DEEP}; height: 10px; margin: 0; }}
QScrollBar::handle {{ background: {SHEET_LINE}; }}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}

QLabel[role="section-title"] {{
    font-family: {SHEET_HEADING_FONT}; font-size: 16px; font-weight: bold; color: {SHEET_HEADING};
}}
QFrame[role="section-rule"] {{ background-color: {SHEET_RULE}; border: none; }}
QFrame[role="form-rule"] {{ background-color: {SHEET_LINE}; border: none; }}
QLabel[role="caption"] {{ font-size: 11px; font-weight: bold; color: {SHEET_TEXT_MUTED}; }}
QLabel[role="note"] {{ font-size: 12px; color: {SHEET_TEXT_MUTED}; }}
QLabel[role="strong"] {{ font-weight: bold; }}
QLabel[role="form-line"] {{ font-size: 14px; }}
QLabel[role="readout"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 17px; font-weight: bold; }}
QLabel[role="tile-title"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 14px; font-weight: bold; color: {SHEET_HEADING}; }}
QLabel[role="stat"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 26px; font-weight: bold; }}
QLabel[role="stat-accent"] {{
    font-family: {SHEET_HEADING_FONT}; font-size: 26px; font-weight: bold; color: {SHEET_ACCENT};
}}
QLabel[role="roll-target"] {{
    font-family: {SHEET_HEADING_FONT}; font-size: 28px; font-weight: bold; color: {SHEET_ACCENT};
    background-color: {SHEET_FIELD}; border: 2px solid {SHEET_ACCENT}; border-radius: 3px; padding: 8px;
}}
QFrame[role="tile"] {{
    background-color: {SHEET_FIELD}; border: 1px solid {SHEET_LINE}; border-radius: 3px;
}}

QPushButton {{
    background-color: {SHEET_DRAB_LIGHT}; color: {SHEET_TEXT}; border: none; border-radius: 3px;
    padding: 6px 14px; font-weight: bold;
}}
QPushButton:hover {{ background-color: {GREEN_DARK}; }}
QPushButton:disabled {{ background-color: {SHEET_SURFACE_DEEP}; color: {SHEET_TEXT_MUTED}; }}
QPushButton[role="skill"] {{
    background-color: transparent; border: none; border-radius: 0; padding: 0;
    border-bottom: 1px dotted {SHEET_LINE};
}}
QPushButton[role="skill"]:hover {{ background-color: {SHEET_SURFACE_DEEP}; }}
QLabel[role="skill-trained"] {{ font-weight: bold; }}
QLabel[role="skill-untrained"] {{ color: {SHEET_TEXT_MUTED}; }}
QFrame[role="pip-on"] {{
    background-color: {SHEET_HEADING}; border: 1px solid {SHEET_HEADING}; border-radius: 6px;
}}
QFrame[role="pip-off"] {{
    background-color: transparent; border: 1px solid {SHEET_TEXT_MUTED}; border-radius: 6px;
}}

QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit {{
    background-color: {SHEET_FIELD}; color: {SHEET_TEXT};
    border: 1px solid {SHEET_LINE}; border-radius: 2px; padding: 3px 5px;
    selection-background-color: {SHEET_DRAB_LIGHT}; selection-color: {SHEET_TEXT};
    placeholder-text-color: {SHEET_TEXT_MUTED};
}}
QSpinBox:disabled, QDoubleSpinBox:disabled, QComboBox:disabled {{
    background-color: {SHEET_SURFACE_DEEP}; color: {SHEET_TEXT_MUTED};
}}
QSpinBox[role="vital"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 24px; font-weight: bold; }}
/* Styling a spin box without these lets the text field cover the up button under the Windows 11 style. */
QSpinBox::up-button, QDoubleSpinBox::up-button {{
    subcontrol-origin: border; subcontrol-position: top right; width: 20px;
    background-color: {SHEET_SURFACE_DEEP}; border-left: 1px solid {SHEET_LINE};
    border-bottom: 1px solid {SHEET_LINE}; border-top-right-radius: 2px;
}}
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    subcontrol-origin: border; subcontrol-position: bottom right; width: 20px;
    background-color: {SHEET_SURFACE_DEEP}; border-left: 1px solid {SHEET_LINE};
    border-bottom-right-radius: 2px;
}}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,
QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {{ background-color: {SHEET_DRAB_LIGHT}; }}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{ background-color: {GREEN_DARK}; }}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{ image: url("{UI_ICONS}/spin_up.svg"); width: 10px; height: 7px; }}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{ image: url("{UI_ICONS}/spin_down.svg"); width: 10px; height: 7px; }}
QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled,
QSpinBox::up-arrow:off, QDoubleSpinBox::up-arrow:off {{ image: url("{UI_ICONS}/spin_up_disabled.svg"); }}
QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled,
QSpinBox::down-arrow:off, QDoubleSpinBox::down-arrow:off {{ image: url("{UI_ICONS}/spin_down_disabled.svg"); }}
QComboBox QAbstractItemView {{
    background-color: {SHEET_FIELD}; color: {SHEET_TEXT}; border: 1px solid {SHEET_LINE};
    selection-background-color: {SHEET_DRAB_LIGHT}; selection-color: {SHEET_TEXT};
}}
QCheckBox {{ spacing: 6px; }}
QCheckBox:disabled {{ color: {SHEET_TEXT_MUTED}; }}
QCheckBox::indicator {{
    width: 13px; height: 13px; background-color: {SHEET_FIELD};
    border: 1px solid {SHEET_TEXT_MUTED}; border-radius: 2px;
}}
QCheckBox::indicator:checked {{ background-color: {SHEET_HEADING}; border-color: {SHEET_HEADING}; }}
QCheckBox::indicator:disabled {{ background-color: {SHEET_SURFACE_DEEP}; border-color: {SHEET_LINE}; }}

QTableWidget {{ background-color: transparent; border: none; }}
QTableWidget::item {{ border-bottom: 1px dotted {SHEET_LINE}; color: {SHEET_TEXT}; }}
QHeaderView::section {{
    background-color: transparent; color: {SHEET_TEXT_MUTED}; font-size: 11px; font-weight: bold;
    border: none; border-bottom: 1px solid {SHEET_LINE}; padding: 2px 4px;
}}

/* Light & Sky page */
QFrame[role="slot"] {{
    background-color: {SHEET_FIELD}; border: 1px solid {SHEET_LINE}; border-radius: 4px;
}}
QFrame[role="slot-filled"] {{
    background-color: {SHEET_FIELD}; border: 1px solid {SHEET_HEADING}; border-radius: 4px;
}}
QFrame[role="slot-super"] {{
    background-color: {SHEET_FIELD}; border: 2px solid {SHEET_SUPER_ENERGY}; border-radius: 4px;
}}
QFrame[role="slot-locked"] {{
    background-color: {SHEET_SURFACE}; border: 1px dashed {SHEET_LINE}; border-radius: 4px;
}}
QFrame[role="slot"] QLabel, QFrame[role="slot-filled"] QLabel,
QFrame[role="slot-super"] QLabel, QFrame[role="slot-locked"] QLabel {{ border: none; background: transparent; }}
QLabel[role="slot-locked-title"] {{
    font-family: {SHEET_HEADING_FONT}; font-size: 18px; font-weight: bold; color: {SHEET_LINE};
}}
QLabel[role="energy-badge"] {{ font-size: 11px; font-weight: bold; color: {SHEET_LIGHT_ENERGY}; }}
QLabel[role="super-badge"] {{ font-size: 11px; font-weight: bold; color: {SHEET_SUPER_ENERGY}; }}
QLabel[role="energy-value"] {{ font-family: {SHEET_HEADING_FONT}; font-size: 22px; font-weight: bold; }}
QLabel[role="status-bad"] {{ color: {SHEET_BAD}; }}
QLabel[role="status-good"] {{ color: {SHEET_GOOD}; }}
QProgressBar {{
    background-color: {SHEET_SURFACE_DEEP}; border: 1px solid {SHEET_LINE}; border-radius: 3px;
    height: 16px; text-align: center; color: {SHEET_SURFACE}; font-weight: bold;
}}
QProgressBar[role="light-energy"]::chunk {{ background-color: {SHEET_LIGHT_ENERGY}; border-radius: 2px; }}
QProgressBar[role="super-energy"]::chunk {{ background-color: {SHEET_SUPER_ENERGY}; border-radius: 2px; }}
"""
