"""Effective characteristics while a character's armor is (or isn't) worn.

A character's saved ``characteristics`` and ``mythic_characteristics`` are
always the base values. When ``armor_equipped`` is true (the default for a
character that has armor), the worn suit's bonuses are added on top:

* the armor record's ``characteristic_bonus`` (``STR``, ``AGI``, ``mythic_STR``,
  ``mythic_AGI``, and penalties such as an E.O.D BDU's -10 ``AGI``), plus
* the soldier type's ``special_rules.mjolnir_armor.bonus_while_worn``
  (Spartan IV: +5 STR, TOU, and AGI in GEN II/III).

When the armor data is unavailable, the bonus saved on the character at
creation (``armor_bonus``) is used instead. No Qt here, so the sheet's
behavior can be unit tested.
"""

from typing import Dict, Optional, Tuple

from .derived_stats import mythic_value
from .starting_armor import worn_bonus

MYTHIC_PREFIX = "mythic_"


def is_equipped(character: dict) -> bool:
    """Armor counts as worn unless the sheet has marked it unequipped."""
    if not character.get("armor"):
        return False
    return bool(character.get("armor_equipped", True))


def armor_bonus(
    character: dict,
    armors: Optional[Dict[str, dict]] = None,
    soldier_data: Optional[dict] = None,
) -> Dict[str, int]:
    """Bonuses the character's armor grants while worn (not whether it is worn)."""
    name = character.get("armor")
    if not name:
        return {}
    if armors and name in armors:
        return worn_bonus(name, soldier_data, armors)
    saved = character.get("armor_bonus")
    return {k: v for k, v in (saved or {}).items() if isinstance(v, int)} if isinstance(saved, dict) else {}


def effective_characteristics(
    character: dict, bonus: Dict[str, int], equipped: bool
) -> Tuple[Dict[str, object], Dict[str, object]]:
    """(characteristics, mythic_characteristics) with worn-armor bonuses applied.

    Unequipped (or no bonus), the character's own values are returned
    unchanged so their display formatting (e.g. "+3") is preserved.
    """
    base = character.get("characteristics")
    base = dict(base) if isinstance(base, dict) else {}
    mythic = character.get("mythic_characteristics")
    mythic = dict(mythic) if isinstance(mythic, dict) else {}
    if not equipped or not bonus:
        return base, mythic
    for key, value in bonus.items():
        if key.startswith(MYTHIC_PREFIX):
            code = key[len(MYTHIC_PREFIX):]
            mythic[code] = mythic_value(mythic.get(code, 0)) + value
        elif isinstance(base.get(key), (int, float)):
            base[key] = max(0, base[key] + value)
    return base, mythic


def effective_character(
    character: dict,
    armors: Optional[Dict[str, dict]] = None,
    soldier_data: Optional[dict] = None,
) -> dict:
    """A copy of the character whose stats reflect worn armor."""
    bonus = armor_bonus(character, armors, soldier_data)
    characteristics, mythic = effective_characteristics(character, bonus, is_equipped(character))
    return {**character, "characteristics": characteristics, "mythic_characteristics": mythic}


def bonus_for(code: str, bonus: Dict[str, int], mythic: bool = False) -> int:
    return bonus.get(f"{MYTHIC_PREFIX}{code}" if mythic else code, 0)
