"""Outlier rules shared by the creator, the XP Shop and the character sheet.

Outlier records come from data/character_creation/outliers.json (Core, burn
1 Luck) and data/light_and_sky/character_creation/outliers.json (Guardians,
burn 2 Luck). Besides ``name`` and ``effect`` a record may carry:

- ``max_times``: how often it can be taken (Enduring, Robust, Vigorous: 2)
- ``max_times_per_characteristic`` / ``max_times_per_mythic``: Aptitude and
  Forte are taken once per pick of a Characteristic, up to this many times each
- ``second_rank_effect``: the effect text when taken twice
- ``chosen_characteristic_bonus`` / ``chosen_mythic_bonus``: Aptitude +5, Forte +1
- ``characteristic_bonus``: fixed bonuses (Imposing: +3 STR and TOU)
- ``support_points``: Advocate +2
- ``learning_intellect_modifier_multiplier``: Acumen x3 for Educations/Languages
- ``ignored_fatigue_levels_per_rank``: Enduring 2 per time taken
- ``natural_healing_multiplier_by_rank``: Vigorous [2, 3]
- Light & Sky ``bonus_*`` keys (see src/models/xp_shop.py LIGHT_BONUS_KEYS)

A character's ``outliers`` list names each outlier once per time taken
(``["Robust", "Robust"]``); ``outlier_choices`` maps Aptitude / Forte to the
codes picked for each take (``{"Aptitude": ["STR", "STR", "AGI"]}``).
No Qt here, so these rules are tested on their own.
"""
from __future__ import annotations

from typing import Any, Iterable, Optional

CHOICE_KEYS = ("max_times_per_characteristic", "max_times_per_mythic")


def _fold(text) -> str:
    return str(text or "").strip().casefold()


def _int(value, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def records(game_data) -> dict[str, dict]:
    """Every outlier record in the loaded data, by folded name."""
    found: dict[str, dict] = {}
    if game_data is None:
        return found
    for document in game_data.families.get("outliers", {}).values():
        outliers = document.get("outliers", {}) if isinstance(document, dict) else {}
        for record in outliers.get("list", []) if isinstance(outliers, dict) else []:
            if isinstance(record, dict) and record.get("name"):
                found.setdefault(_fold(record["name"]), record)
    return found


def record(game_data, name) -> dict:
    return records(game_data).get(_fold(name), {})


def needs_choice(outlier: dict) -> Optional[str]:
    """"characteristic" (Aptitude), "mythic" (Forte), or None."""
    if outlier.get("max_times_per_characteristic"):
        return "characteristic"
    if outlier.get("max_times_per_mythic"):
        return "mythic"
    return None


def max_times(outlier: dict) -> int:
    """Times an outlier without a per-characteristic choice can be taken."""
    return max(1, _int(outlier.get("max_times"), 1))


def max_per_choice(outlier: dict) -> int:
    for key in CHOICE_KEYS:
        if outlier.get(key):
            return max(1, _int(outlier[key], 1))
    return 1


def can_take(outlier: dict, taken: Iterable[str], choices: Iterable[str] = (), choice: Optional[str] = None) -> bool:
    """Whether one more of ``outlier`` is allowed.

    ``taken`` is the character's outliers list; ``choices`` the codes already
    picked for this outlier (Aptitude / Forte); ``choice`` the code for this take.
    """
    name = _fold(outlier.get("name"))
    if needs_choice(outlier):
        if not choice:
            return False
        return [_fold(code) for code in choices].count(_fold(choice)) < max_per_choice(outlier)
    return [_fold(value) for value in taken].count(name) < max_times(outlier)


def times_taken(character: dict, name) -> int:
    return [_fold(value) for value in character.get("outliers") or []].count(_fold(name))


def effect_text(outlier: dict, times: int = 1) -> str:
    """The effect at the rank taken (Enduring / Vigorous taken twice read differently)."""
    if times >= 2 and outlier.get("second_rank_effect"):
        return outlier["second_rank_effect"]
    return outlier.get("effect", "")


def total(game_data, character: dict, key: str) -> int:
    """Sum of a numeric field over every outlier taken (each take counts)."""
    by_name = records(game_data)
    return sum(
        _int(by_name.get(_fold(name), {}).get(key))
        for name in character.get("outliers") or []
    )


def support_points(game_data, character: dict) -> int:
    """Support Points from outliers (Advocate +2)."""
    return total(game_data, character, "support_points")


def learning_multiplier(game_data, character: dict) -> int:
    """Intellect Modifier multiplier for Education and Language limits (Acumen x3)."""
    multiplier = 1
    for name in set(_fold(value) for value in character.get("outliers") or []):
        value = _int(record(game_data, name).get("learning_intellect_modifier_multiplier"))
        multiplier = max(multiplier, value)
    return multiplier


def ignored_fatigue_levels(game_data, character: dict) -> int:
    """Fatigue levels whose penalties are ignored (Enduring 2 per take, so 2 or 4)."""
    return total(game_data, character, "ignored_fatigue_levels_per_rank")


def natural_healing_multiplier(game_data, character: dict) -> int:
    """Natural Healing multiplier (Vigorous: x2 once, x3 twice)."""
    multiplier = 1
    for name in set(_fold(value) for value in character.get("outliers") or []):
        ranks = record(game_data, name).get("natural_healing_multiplier_by_rank")
        if isinstance(ranks, list) and ranks:
            times = times_taken(character, name)
            multiplier = max(multiplier, _int(ranks[min(times, len(ranks)) - 1], 1))
    return multiplier


def summary(game_data, character: dict) -> list[dict[str, Any]]:
    """One entry per distinct outlier taken: name, times, picks and effect text."""
    choices = character.get("outlier_choices")
    choices = choices if isinstance(choices, dict) else {}
    seen, rows = set(), []
    for name in character.get("outliers") or []:
        folded = _fold(name)
        if folded in seen:
            continue
        seen.add(folded)
        outlier = record(game_data, name) or {"name": name}
        times = times_taken(character, name)
        picks = [code for code in choices.get(outlier.get("name", name), []) if code]
        rows.append({
            "name": outlier.get("name", name),
            "times": times,
            "picks": picks,
            "effect": effect_text(outlier, times),
        })
    return rows
