"""Spartan starting armor: pick a Mjolnir/SPI suit and, for Mjolnir, a variant.

Spartan soldier types list their choices in
``special_rules.mjolnir_armor.armor_options`` as
``{"armor": <unsc_armor record name>, "years": "2525–2551", "label": ...}``.
The years are the book's "Armor Usage" spans; the app has no campaign year,
so they are shown as guidance and not enforced (the book lets the GM allow
older armor or SPI anyway).

A Mjolnir suit's ``variant_generations`` lists which GEN I/II/III variant
tables it may use (unsc_armor_variants.json). "Default Armors" rows are the
no-variant option, so they are not offered as variants; choosing no variant
keeps the standard suit. Variant prices are recorded but not charged:
characters start with no credits in the creator.
"""

from typing import Dict, List, Optional

GENERATION_KEYS = {"GEN I": "gen_i", "GEN II": "gen_ii", "GEN III": "gen_iii"}
NO_VARIANT_NAMES = {"Default Armors"}
BONUS_ORDER = ("STR", "mythic_STR", "TOU", "AGI", "mythic_AGI")


def armor_rules(soldier_data: Optional[dict]) -> dict:
    return ((soldier_data or {}).get("special_rules") or {}).get("mjolnir_armor") or {}


def armor_options(soldier_data: Optional[dict]) -> List[dict]:
    """The soldier type's starting-armor choices (empty for non-Spartans)."""
    return [
        option
        for option in armor_rules(soldier_data).get("armor_options", [])
        if isinstance(option, dict) and option.get("armor")
    ]


def variant_tables(game_data) -> Dict[str, List[dict]]:
    doc = game_data.get("unsc_armor_variants", "unsc_armor_variants") if game_data else None
    return (doc or {}).get("mjolnir_variants", {}) or {}


def variants_for(armor_record: Optional[dict], game_data) -> List[dict]:
    """Variants this suit may take, grouped in generation order."""
    tables = variant_tables(game_data)
    variants = []
    for generation in (armor_record or {}).get("variant_generations", []) or []:
        for variant in tables.get(GENERATION_KEYS.get(generation, ""), []):
            if variant.get("name") not in NO_VARIANT_NAMES:
                variants.append(variant)
    return variants


def variant_label(variant: dict) -> str:
    return f"{variant['name']} ({variant['generation']}) - {variant.get('price', 0)} cR"


def find_variant(game_data, generation: str, name: str) -> Optional[dict]:
    for variant in variant_tables(game_data).get(GENERATION_KEYS.get(generation, ""), []):
        if variant.get("name") == name:
            return variant
    return None


def worn_bonus(armor_name: Optional[str], soldier_data: Optional[dict], armors: Dict[str, dict]) -> Dict[str, int]:
    """Characteristic bonuses while wearing this suit (suit + soldier-type rule)."""
    total: Dict[str, int] = {}
    record = armors.get(armor_name or "") or {}
    for key, value in (record.get("characteristic_bonus") or {}).items():
        if isinstance(value, int) and value:
            total[key] = total.get(key, 0) + value
    extra = armor_rules(soldier_data).get("bonus_while_worn") or {}
    if armor_name in (extra.get("armor") or []):
        for key, value in (extra.get("characteristics") or {}).items():
            if isinstance(value, int) and value:
                total[key] = total.get(key, 0) + value
    ordered = [key for key in BONUS_ORDER if key in total]
    ordered += [key for key in total if key not in BONUS_ORDER]
    return {key: total[key] for key in ordered}


def format_bonus(bonus: Optional[Dict[str, int]]) -> str:
    """'+20 STR, +3 Mythic STR, +15 AGI'."""
    parts = []
    for key, value in (bonus or {}).items():
        label = f"Mythic {key[len('mythic_'):]}" if key.startswith("mythic_") else key
        parts.append(f"{value:+d} {label}")
    return ", ".join(parts)


def variant_entry(variant: Optional[dict]) -> Optional[dict]:
    """What a character stores for its variant."""
    if not variant:
        return None
    return {
        "name": variant["name"],
        "generation": variant["generation"],
        "price": variant.get("price", 0),
    }


def validate_choice(
    soldier_data: Optional[dict],
    armor_name: Optional[str],
    variant: Optional[dict],
    armors: Dict[str, dict],
    game_data,
) -> List[str]:
    """Problems with a starting-armor pick; empty when it is allowed."""
    problems = []
    allowed = [option["armor"] for option in armor_options(soldier_data)]
    if armor_name not in allowed:
        problems.append(f"'{armor_name}' is not a starting armor option for this soldier type")
        return problems
    if armor_name not in armors:
        problems.append(f"Unknown armor '{armor_name}'")
        return problems
    if variant:
        names = {(v["generation"], v["name"]) for v in variants_for(armors[armor_name], game_data)}
        if (variant.get("generation"), variant.get("name")) not in names:
            problems.append(
                f"Variant '{variant.get('name')}' ({variant.get('generation')}) "
                f"cannot be used with {armor_name}"
            )
    return problems
