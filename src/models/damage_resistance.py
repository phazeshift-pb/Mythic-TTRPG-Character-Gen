"""Damage Resistance per body location (Mythic 7.0 CU1, Damage and Pierce).

Damage Resistance = Toughness Modifier + Mythic Toughness + the worn armor's
Armor Rating for the location struck (Head, Chest, Arms, Legs).

Armor Ratings come from the UNSC armor record (``armor_rating``) or, for
Light & Sky loot armor, the rolled ``armor_values``. Mjolnir variants only
describe their armor changes in text ("-1 Armor to the Chest location",
"+2 Armor to all Locations"), so ``variant_armor_modifiers`` reads those
sentences. Conditional bonuses ("+10 Armor against Melee Attacks") are
left out because they don't always apply.

No Qt here, so the sheet's numbers can be unit tested.
"""

import re
from typing import Dict, Optional

from .derived_stats import characteristic_modifier, mythic_value
from .starting_armor import find_variant
from . import worn_armor

# (key, label, hit-location roll)
LOCATIONS = (
    ("head", "Head", "01-10"),
    ("chest", "Chest", "61-100"),
    ("arms", "Arms", "11-30"),
    ("legs", "Legs", "31-60"),
)
SLOTS = tuple(key for key, _, _ in LOCATIONS)

_LOCATION_WORDS = {
    "head": r"\b(head|helmet)",
    "chest": r"\b(chest|torso)",
    "arms": r"\barms?\b",
    "legs": r"\blegs?\b",
}
_CONDITIONAL = re.compile(r"\bagainst\b|when dealing|armor interface", re.IGNORECASE)
_SIGNED = re.compile(r"([+-])\s?(\d+)")
# What may sit between the number and the word Armor ("+2 to Armor", "-3 Penalty to all Armor")
_TO_ARMOR = re.compile(
    r"^\s*(?:bonus\s+|penalty\s+)?(?:armor\b|(?:to|on|in)\s+(?:all\s+|the\s+)?armor\b|"
    r"(?:to|on|in)\s+all\s+(?:armor\s+)?locations?\b)",
    re.IGNORECASE,
)


def _locations_in(text: str) -> list:
    if re.search(r"\ball\b", text, re.IGNORECASE):
        return list(SLOTS)
    return [slot for slot, pattern in _LOCATION_WORDS.items() if re.search(pattern, text, re.IGNORECASE)]


def variant_armor_modifiers(description: Optional[str]) -> Dict[str, int]:
    """Armor Rating changes a Mjolnir variant's description states, by location."""
    totals: Dict[str, int] = {}
    for sentence in re.split(r"(?<=\.)\s+", str(description or "")):
        if "armor" not in sentence.lower() or _CONDITIONAL.search(sentence):
            continue
        for match in _SIGNED.finditer(sentence):
            after = sentence[match.end():]
            bonus_only = re.match(r"^\s*bonus\b", after, re.IGNORECASE) and re.search(
                r"armor\s+location", sentence[: match.start()], re.IGNORECASE
            )
            if not (_TO_ARMOR.match(after) or bonus_only):
                continue
            value = int(match.group(2)) * (-1 if match.group(1) == "-" else 1)
            # Locations named after the number ("to the Chest"), else before it ("Helmet gains +4")
            tail = re.split(_SIGNED, after, maxsplit=1)[0]
            slots = _locations_in(tail) or _locations_in(sentence[: match.start()])
            for slot in slots:
                totals[slot] = totals.get(slot, 0) + value
    return {slot: totals[slot] for slot in SLOTS if totals.get(slot)}


def conditional_armor_notes(description: Optional[str]) -> list:
    """Situational armor sentences (e.g. "+10 Armor against Melee Attacks") left out of the totals."""
    notes = []
    for sentence in re.split(r"(?<=\.)\s+", str(description or "")):
        if re.search(r"\barmor\b", sentence, re.IGNORECASE) and _SIGNED.search(sentence) and re.search(
            r"\bagainst\b|when dealing", sentence, re.IGNORECASE
        ):
            notes.append(sentence.strip())
    return notes


def _int(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def armor_ratings(character: dict, armors: Optional[dict], game_data=None) -> dict:
    """The worn armor's rating per location, before variants.

    Returns {"name", "ratings", "variant", "variant_modifiers", "found", "equipped"}.
    """
    name = character.get("armor") or ""
    equipped = worn_armor.is_equipped(character)
    result = {
        "name": name, "ratings": {}, "variant": None,
        "variant_modifiers": {}, "variant_notes": [], "found": False, "equipped": equipped,
    }
    if not name:
        return result
    loot = character.get("armor_loot")
    if isinstance(loot, dict) and loot.get("armor_values") and _loot_is_worn(character, loot):
        result["ratings"] = {slot: _int(loot["armor_values"].get(slot)) for slot in SLOTS}
        result["found"] = True
    else:
        record = (armors or {}).get(name) or {}
        rating = record.get("armor_rating")
        if isinstance(rating, dict):
            result["ratings"] = {slot: _int(rating.get(slot)) for slot in SLOTS}
            result["found"] = True
    variant = character.get("armor_variant")
    if isinstance(variant, dict) and variant.get("name"):
        record = find_variant(game_data, variant.get("generation", ""), variant["name"]) if game_data else None
        description = (record or variant).get("description", "")
        result["variant"] = variant["name"]
        result["variant_modifiers"] = variant_armor_modifiers(description)
        result["variant_notes"] = conditional_armor_notes(description)
    return result


def _loot_is_worn(character: dict, loot: dict) -> bool:
    from src.loot.character_loot import armor_name

    return character.get("armor") == armor_name(loot)


def damage_resistance(
    toughness,
    mythic_toughness=0,
    armor: Optional[dict] = None,
    other: Optional[Dict[str, int]] = None,
) -> Dict[str, dict]:
    """Per-location breakdown: {slot: {"armor", "variant", "toughness", "mythic", "other", "total"}}.

    ``armor`` is armor_ratings()'s result; unequipped armor gives 0 Armor.
    """
    armor = armor or {}
    worn = armor.get("equipped", False)
    toughness_mod = characteristic_modifier(_int(toughness))
    mythic = mythic_value(mythic_toughness)
    table = {}
    for slot in SLOTS:
        armor_value = (armor.get("ratings") or {}).get(slot, 0) if worn else 0
        variant_value = (armor.get("variant_modifiers") or {}).get(slot, 0) if worn else 0
        extra = _int((other or {}).get(slot, 0))
        parts = {
            "armor": armor_value,
            "variant": variant_value,
            "toughness": toughness_mod,
            "mythic": mythic,
            "other": extra,
        }
        parts["total"] = max(0, sum(parts.values()))
        table[slot] = parts
    return table
