"""Putting rolled Light & Sky loot onto a character, and describing it.

* A rolled weapon is appended to ``character["weapons"]`` as
  ``{"name", "quantity", "source": "light_and_sky_loot", "loot": <roll>}``.
  The sheet's weapon line reads its stats from ``loot`` (see
  equipment_packs.weapon_summary).
* A rolled armor set becomes the worn ``armor``. Its full roll is kept in
  ``armor_loot`` and its Agility modifier is saved as ``armor_bonus`` so the
  sheet's worn-armor effects (movement, carrying capacity, skill tests) use it.

Also builds the loot-card HTML shown in the loot dialog. No Qt here.
"""

from html import escape
from pathlib import Path
from typing import List, Optional

from .loot_rules import CARD_INK_COLORS

LOOT_SOURCE = "light_and_sky_loot"
ASSETS_ROOT = Path(__file__).resolve().parents[2] / "assets" / "light_and_sky"


# ---------------------------------------------------------
# Names and icons
# ---------------------------------------------------------
def format_perk_name(name) -> str:
    """Perk names as written in the data; underscores only as an ID fallback."""
    return str(name or "").replace("_", " ")


def weapon_name(roll: dict) -> str:
    return f"{roll.get('rarity', '')} {roll.get('element', '')} {roll.get('weapon_type', '')}".strip()


def armor_name(roll: dict) -> str:
    return f"{roll.get('rarity', '')} {roll.get('material', '')} Armor Set".strip()


def element_icon(element: str) -> Optional[str]:
    name = str(element or "").lower()
    path = ASSETS_ROOT / "elements" / f"{name}.{'png' if name == 'strand' else 'svg'}"
    return path.as_posix() if path.exists() else None


def ammo_icon(ammo_type: str) -> Optional[str]:
    path = ASSETS_ROOT / "ammo" / f"{str(ammo_type or '').lower()}.svg"
    return path.as_posix() if path.exists() else None


# ---------------------------------------------------------
# Applying loot to a character dict
# ---------------------------------------------------------
def weapon_entry(roll: dict) -> dict:
    return {
        "name": weapon_name(roll),
        "quantity": 1,
        "source": LOOT_SOURCE,
        "loot": dict(roll),
    }


def add_weapon(character: dict, roll: dict) -> dict:
    """Append a rolled weapon to the character's weapons; returns the entry."""
    entry = weapon_entry(roll)
    weapons = character.get("weapons")
    if not isinstance(weapons, list):
        weapons = [weapons] if weapons else []
    weapons.append(entry)
    character["weapons"] = weapons
    return entry


def equip_armor(character: dict, roll: dict) -> str:
    """Make a rolled armor set the character's worn armor; returns its name."""
    name = armor_name(roll)
    agility = int(roll.get("agility_modifier") or 0)
    character["armor"] = name
    character["armor_variant"] = None
    character["armor_bonus"] = {"AGI": agility} if agility else {}
    character["armor_equipped"] = True
    character["armor_loot"] = dict(roll)
    return name


def worn_loot_armor(character: dict) -> Optional[dict]:
    """The rolled armor record, if the character's worn armor is loot."""
    loot = character.get("armor_loot")
    if isinstance(loot, dict) and character.get("armor") == armor_name(loot):
        return loot
    return None


# ---------------------------------------------------------
# Sheet text
# ---------------------------------------------------------
def perk_names(roll: dict) -> List[str]:
    return [format_perk_name(p.get("name")) for p in roll.get("perks") or [] if isinstance(p, dict)]


def perk_line(roll: dict) -> str:
    """'Perks: A, B | Exotic: C' (empty when there are none)."""
    parts = []
    names = perk_names(roll)
    if names:
        parts.append("Perks: " + ", ".join(names))
    exotic = roll.get("exotic_perk")
    if isinstance(exotic, dict) and exotic.get("name"):
        parts.append("Exotic: " + format_perk_name(exotic["name"]))
    return " | ".join(parts)


def perk_descriptions(roll: dict) -> str:
    """Multi-line 'Name: description' text, for tooltips."""
    lines = []
    for perk in roll.get("perks") or []:
        if isinstance(perk, dict):
            lines.append(f"{format_perk_name(perk.get('name'))}: {perk.get('description', '')}")
    exotic = roll.get("exotic_perk")
    if isinstance(exotic, dict) and exotic.get("name"):
        lines.append(f"Exotic - {format_perk_name(exotic['name'])}: {exotic.get('description', '')}")
    return "\n".join(lines)


def armor_sheet_lines(roll: dict) -> List[str]:
    values = roll.get("armor_values") or {}
    lines = [
        armor_name(roll) + " - " + ", ".join(
            f"{slot.title()} {values[slot]}" for slot in ("head", "arms", "chest", "legs") if slot in values
        ),
        f"{roll.get('subtype', '')}, {roll.get('variant', '')}; {roll.get('weight', '')} kg",
    ]
    perks = perk_line(roll)
    if perks:
        lines.append(perks)
    return lines


# ---------------------------------------------------------
# Loot card
# ---------------------------------------------------------
def format_agility(value) -> str:
    return f"+{value}" if value > 0 else str(value)


def card_stats(roll: dict):
    if roll.get("kind") == "weapon":
        return [
            ("Element", roll.get("element")),
            ("Rate of Fire", roll.get("rate_of_fire")),
            ("Damage", f"{roll.get('damage')} + {roll.get('bonus_damage')}"),
            ("Pierce", roll.get("pierce")), ("Range", roll.get("range")),
            ("Magazine", roll.get("magazine")), ("Reload", roll.get("reload")),
            ("Ammo", roll.get("ammo_type")), ("Tags", ", ".join(roll.get("tags") or [])),
        ]
    values = roll.get("armor_values") or {}
    stats = [
        ("Head", values.get("head")), ("Weight", f"{roll.get('weight')} kg"),
        ("Chest", values.get("chest")), ("Subtype", roll.get("subtype")),
        ("Arms", values.get("arms")), ("Variant", roll.get("variant")),
        ("Legs", values.get("legs")),
    ]
    if roll.get("agility_modifier"):
        stats.append(("Agility", format_agility(roll["agility_modifier"])))
    return stats


def loot_card_html(roll: dict) -> str:
    """The loot card from the standalone generator, for a weapon or armor roll."""
    rarity = roll.get("rarity", "Common")
    color = CARD_INK_COLORS.get(rarity, "#55544e")
    is_weapon = roll.get("kind") == "weapon"
    title = roll.get("weapon_type") if is_weapon else f"{roll.get('material')} Armor Set"

    stats = card_stats(roll)
    rows = []
    for index in range(0, len(stats), 2):
        cells = [
            "<td width='50%' style='padding: 8px 10px; border-bottom: 1px solid #d8d7d1;'>"
            f"<span style='font-size: 12px; color: #66655f;'>{escape(label.upper())}</span><br>"
            f"<b style='font-size: 19px; color: #171717;'>{escape(str(value))}</b></td>"
            for label, value in stats[index:index + 2]
        ]
        if len(cells) == 1:
            cells.append("<td width='50%' style='border-bottom: 1px solid #d8d7d1;'></td>")
        rows.append(f"<tr>{''.join(cells)}</tr>")
    special_rules = roll.get("special_rules") or []
    if special_rules:
        rows.append(
            "<tr><td colspan='2' style='padding: 8px 10px; border-bottom: 1px solid #d8d7d1;'>"
            "<span style='font-size: 12px; color: #66655f;'>SPECIAL RULES</span><br>"
            f"<b style='font-size: 16px; color: #171717;'>"
            f"{', '.join(escape(str(r)) for r in special_rules)}</b></td></tr>"
        )

    icons = [element_icon(roll.get("element")), ammo_icon(roll.get("ammo_type"))] if is_weapon else []
    icon_cells = "".join(
        f"<td align='center' style='padding: 4px 10px;'>"
        f"<img src='{escape(icon, quote=True)}' width='56' height='56'></td>"
        for icon in icons if icon
    )
    icon_row = (
        f"<table align='center' cellspacing='0'><tr>{icon_cells}</tr></table>" if icon_cells else ""
    )

    perk_rows = "".join(
        f"<tr><td style='padding: 5px 10px; color: #24231f; font-size: 18px;'>&#8226; {escape(name)}</td></tr>"
        for name in perk_names(roll)
    ) or "<tr><td style='padding: 5px 10px; color: #777;'>None</td></tr>"
    exotic = roll.get("exotic_perk")
    exotic_row = ""
    if isinstance(exotic, dict) and exotic.get("name"):
        exotic_row = (
            "<table width='100%' cellspacing='0' cellpadding='0' style='margin-top: 12px;'>"
            f"<tr><td style='padding: 10px; background-color: #f1eddb; border-left: 4px solid {color};'>"
            f"<b style='font-size: 18px; color: {color};'>Exotic Perk: "
            f"{escape(format_perk_name(exotic['name']))}</b></td></tr></table>"
        )

    return f"""
<div style="background-color: #e9e7df; color: #171717;">
<table width="100%" cellspacing="0" cellpadding="0"><tr>
<td style="padding: 10px 4px;"><b style="font-size: 25px; color: #171717;">{escape(str(title))}</b><br>
<span style="font-size: 13px; color: #66655f;">LIGHT &amp; SKY</span></td>
<td align="right" style="padding: 10px 4px;"><b style="font-size: 15px; color: {color};">{escape(rarity.upper())}</b></td>
</tr></table>
<hr color="{color}" size="3">
{icon_row}
<table width="100%" cellspacing="0" cellpadding="0">{''.join(rows)}</table>
<br>
<table width="100%" cellspacing="0" cellpadding="0">
<tr><td style="padding: 8px 10px; background-color: #dcdad2; border-bottom: 2px solid {color};">
<b style="font-size: 17px; color: #24231f;">PERKS</b></td></tr>
{perk_rows}
</table>
{exotic_row}
</div>
"""
