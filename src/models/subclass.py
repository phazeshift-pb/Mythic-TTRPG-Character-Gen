"""Light & Sky Guardian sub-classes: changing one between missions.

Light and Sky: "Sub-Classes can be changed between missions, refunding all
Characteristics or other benefits gained from them." A sub-class only grants
the characteristic modifiers listed under its Guardian class
(``subclasses.<name>.characteristic_modifiers``), so a change takes the old
sub-class's modifiers back off and puts the new one's on.

The character dict records the current sub-class as ``subclass``. Files saved
before that field existed have it in ``selections.initial_setup.subclass``;
the loader copies it across. No Qt here.
"""
from __future__ import annotations

from typing import Any, Optional

from .derived_stats import max_wounds


def _int(value, default: int = 0) -> int:
    try:
        return int(str(value).replace("+", "", 1))
    except (TypeError, ValueError):
        return default


def guardian_record(game_data, soldier_type_name) -> dict:
    """The Guardian class record whose name matches the character's soldier type."""
    if game_data is None or not soldier_type_name:
        return {}
    for record in game_data.families.get("soldier_type", {}).values():
        if (
            isinstance(record, dict)
            and record.get("name") == soldier_type_name
            and isinstance(record.get("subclasses"), dict)
            and record["subclasses"]
        ):
            return record
    return {}


def subclass_names(game_data, character: dict) -> list[str]:
    return list(guardian_record(game_data, character.get("soldier_type")).get("subclasses", {}))


def modifiers(game_data, character: dict, subclass: Optional[str]) -> dict[str, int]:
    """Characteristic modifiers a sub-class grants, e.g. {"TOU": 10, "STR": -5}."""
    if not subclass:
        return {}
    record = guardian_record(game_data, character.get("soldier_type"))
    data = (record.get("subclasses") or {}).get(subclass) or {}
    return {
        code: _int(value)
        for code, value in (data.get("characteristic_modifiers") or {}).items()
        if _int(value)
    }


def change_preview(game_data, character: dict, new_subclass: str) -> dict[str, int]:
    """Net characteristic change of switching to ``new_subclass`` (zero changes left out)."""
    old = modifiers(game_data, character, character.get("subclass"))
    new = modifiers(game_data, character, new_subclass)
    return {
        code: new.get(code, 0) - old.get(code, 0)
        for code in sorted(set(old) | set(new))
        if new.get(code, 0) - old.get(code, 0)
    }


def change_subclass(game_data, character: dict, new_subclass: str) -> dict[str, int]:
    """Switch sub-class in place, refunding the old one's modifiers. Returns the net change.

    With no recorded sub-class there is nothing known to refund, so the new
    one is only recorded (its modifiers are assumed to be in the totals
    already). Current Wounds move with Max Wounds.
    """
    names = subclass_names(game_data, character)
    if new_subclass not in names:
        raise ValueError(f"{new_subclass} is not a sub-class of {character.get('soldier_type')}")
    if not character.get("subclass"):
        character["subclass"] = new_subclass
        return {}
    if character["subclass"] == new_subclass:
        return {}
    change = change_preview(game_data, character, new_subclass)
    wounds_before = _max_wounds(character)
    characteristics = dict(character.get("characteristics") or {})
    for code, delta in change.items():
        characteristics[code] = _int(characteristics.get(code)) + delta
    character["characteristics"] = characteristics
    character["subclass"] = new_subclass
    # Current Wounds follow Max Wounds up (as XP Shop Toughness does) and are
    # capped when it drops.
    wounds_after = _max_wounds(character)
    current = _int(character.get("wounds"))
    if wounds_after > wounds_before:
        character["wounds"] = current + (wounds_after - wounds_before)
    elif current > wounds_after:
        character["wounds"] = wounds_after
    return change


def _max_wounds(character: dict) -> int:
    return max_wounds(
        _int((character.get("characteristics") or {}).get("TOU")),
        (character.get("mythic_characteristics") or {}).get("TOU", 0),
        list(character.get("outliers") or []).count("Robust"),
        flat_bonus=_int(character.get("wounds_modifier")),
    )


def describe(change: dict[str, Any]) -> str:
    return ", ".join(f"{delta:+d} {code}" for code, delta in change.items()) or "no characteristic change"
