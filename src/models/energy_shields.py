"""Energy Shields for a character (Mythic 7.0 CU1 and Light and Sky).

Core (Mythic 7.0 CU1, Energy Shield Rules p. 109-110): shields come from
the worn armor. Only some suits have them (Mark V/VI/VII, GEN II/III Mjolnir,
the Headhunter SPI); the armor record's ``energy_shields`` holds Integrity,
Recharge Delay and Recharge Rate. Mjolnir variants may add to them in their
description ("+50 to Shield Integrity and +25 to Shield Recharge").
SPI armor halves Recharge Rate and doubles Delay while its Photo-Reactive
Panels are active.

Light and Sky (Armor Engram System, Light Shielding): every Guardian wearing
Guardian armor (armor rolled from the Light & Sky engram tables) has an
Energy Shield of 125 Integrity, 5 Delay, 50 Recharge.

No Qt here, so the sheet's numbers can be unit tested.
"""

import re
from typing import Optional

from .starting_armor import find_variant
from . import worn_armor

LIGHT_AND_SKY = "Light & Sky"
GUARDIAN_CLASSES = ("hunter", "titan", "warlock")
LIGHT_SHIELDING = {"integrity": 125, "delay": 5, "recharge": 50}
SPI_TRAIT = "SPI Shield Power Consumption"

# Book reminders shown with the shield (Energy Shield Rules)
RULE_NOTES = (
    "Damage hits Shield Integrity first; once it reaches 0, leftover Damage hits the "
    "character (Pierce doesn't carry over).",
    "Weapons with Penetration, Spread, Cauterize, Kinetic, Blast/Kill, Carpet or "
    "Electrified also deal their Pierce to the shield.",
    "Explosives triple their Pierce against shields.",
    "Taking 10 or more Damage in a Round resets the Recharge Delay.",
    "Combined Action Attacks deal +10 Damage to the shield per character involved, per Half Action.",
)

_SIGNED = re.compile(r"([+-])\s?(\d+)")
_STAT_AFTER = re.compile(
    r"^\s*(?:bonus\s+)?(?:to\s+)?(?:the\s+)?(?:energy\s+)?"
    r"(shield\s+integrity|shield\s+recharge(?:\s+rate)?|recharge\s+rate|shield\s+delay|"
    r"recharge\s+delay|shields?\b)",
    re.IGNORECASE,
)


def variant_shield_modifiers(description: Optional[str]) -> dict:
    """Shield changes a Mjolnir variant's description states: {"integrity", "delay", "recharge"}."""
    totals = {}
    for match in _SIGNED.finditer(str(description or "")):
        stat = _STAT_AFTER.match(description[match.end():])
        if not stat:
            continue
        words = stat.group(1).lower()
        key = "delay" if "delay" in words else "recharge" if "recharge" in words else "integrity"
        value = int(match.group(2)) * (-1 if match.group(1) == "-" else 1)
        totals[key] = totals.get(key, 0) + value
    return totals


def is_guardian(character: dict, ruleset: str) -> bool:
    soldier = str(character.get("soldier_type") or "").split()
    return ruleset == LIGHT_AND_SKY and bool(soldier) and soldier[0].lower() in GUARDIAN_CLASSES


def _wears_guardian_armor(character: dict) -> bool:
    from src.loot.character_loot import worn_loot_armor

    return worn_loot_armor(character) is not None


def _int(value) -> int:
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def energy_shield(
    character: dict,
    armors: Optional[dict] = None,
    ruleset: str = "",
    game_data=None,
    *,
    panels_active: bool = False,
    other_integrity: int = 0,
) -> dict:
    """The character's Energy Shield right now.

    Returns {"has_shield", "source", "integrity", "delay", "recharge", "base",
    "variant", "variant_modifiers", "spi", "notes"}.
    """
    result = {
        "has_shield": False, "source": "", "integrity": 0, "delay": 0, "recharge": 0,
        "base": {}, "variant": None, "variant_modifiers": {}, "spi": False, "notes": [],
    }
    name = character.get("armor") or ""
    equipped = worn_armor.is_equipped(character)
    record = (armors or {}).get(name) or {}
    guardian = is_guardian(character, ruleset)

    if not name:
        result["notes"].append(
            "Guardians gain Light Shielding by wearing Guardian armor." if guardian else "No armor worn."
        )
        return result
    if not equipped:
        result["notes"].append(f"{name} is removed, so it gives no Energy Shield.")
        return result

    shields = record.get("energy_shields")
    if isinstance(shields, dict) and shields.get("integrity"):
        base = {key: _int(shields.get(key)) for key in ("integrity", "delay", "recharge")}
        result["source"] = name
        variant = character.get("armor_variant")
        if isinstance(variant, dict) and variant.get("name"):
            found = find_variant(game_data, variant.get("generation", ""), variant["name"]) if game_data else None
            mods = variant_shield_modifiers((found or variant).get("description", ""))
            result["variant"] = variant["name"]
            result["variant_modifiers"] = mods
        result["spi"] = any(
            isinstance(trait, dict) and trait.get("name") == SPI_TRAIT for trait in record.get("traits", [])
        )
    elif guardian and _wears_guardian_armor(character):
        base = dict(LIGHT_SHIELDING)
        result["source"] = "Light Shielding (Guardian armor)"
    else:
        if guardian:
            result["notes"].append(
                f"{name} isn't Guardian armor, so it gives no Light Shielding."
            )
        else:
            result["notes"].append(f"{name} has no Energy Shields.")
        return result

    stats = {key: base[key] + result["variant_modifiers"].get(key, 0) for key in base}
    stats["integrity"] += _int(other_integrity)
    if result["spi"]:
        if panels_active:
            stats["recharge"] //= 2
            stats["delay"] *= 2
            result["notes"].append("Photo-Reactive Panels active: Recharge Rate halved, Delay doubled.")
        else:
            result["notes"].append("While the Photo-Reactive Panels are active, Recharge Rate halves and Delay doubles.")
    result.update(base=base, has_shield=stats["integrity"] > 0, **{k: max(0, v) for k, v in stats.items()})
    return result


def recharge(current: int, shield: dict) -> int:
    """Shield Integrity after one Round of recharging (never above Integrity)."""
    return min(shield.get("integrity", 0), max(0, _int(current)) + shield.get("recharge", 0))
