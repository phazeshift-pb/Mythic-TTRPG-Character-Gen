"""Shared colours and Qt stylesheets for the creator and character sheet.

Change a colour here and every page that uses these styles follows.
Page-specific one-off styles can stay inline next to their widget.
"""

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
