"""Pure derived-stat rules for Mythic characters.

No Qt, no GameData: everything here takes plain numbers so it can be unit
tested and shared by the model, the creator UI and the character sheet.
The defaults mirror data/character_creation/wounds_formula.json and
data/character_creation/outliers.json; tests/test_derived_stats.py checks
they have not drifted.
"""

from typing import Any

WOUNDS_BASE = 40
WOUNDS_PER_TOUGHNESS_MODIFIER = 2
WOUNDS_PER_MYTHIC_TOUGHNESS = 2
ROBUST_WOUNDS = 18  # per Robust outlier taken (max 2)


def characteristic_modifier(value: int) -> int:
    """Characteristic modifier: floor(value / 10)."""
    return int(value) // 10


def mythic_value(raw: Any) -> int:
    """Mythic scores are stored as ints or strings such as '+3'."""
    if isinstance(raw, str):
        try:
            return int(raw.strip())
        except ValueError:
            return 0
    return int(raw) if isinstance(raw, (int, float)) else 0


def max_wounds(
    toughness: int,
    mythic_toughness: Any = 0,
    robust_count: int = 0,
    *,
    base: int = WOUNDS_BASE,
    toughness_multiplier: int = WOUNDS_PER_TOUGHNESS_MODIFIER,
    mythic_multiplier: int = WOUNDS_PER_MYTHIC_TOUGHNESS,
    robust_bonus: int = ROBUST_WOUNDS,
) -> int:
    """Wounds = 40 + (TOU modifier x 2) + (Mythic TOU x 2) + 18 per Robust."""
    return (
        base
        + characteristic_modifier(toughness) * toughness_multiplier
        + mythic_value(mythic_toughness) * mythic_multiplier
        + max(0, int(robust_count)) * robust_bonus
    )


def fatigue_coma_threshold(toughness: int) -> int:
    """Fatigue at which a character falls into a coma: TOU modifier x 2."""
    return characteristic_modifier(toughness) * 2
