"""Soldier-type equipment packs linked to the UNSC Armory.

An ``equipment_sets`` pack is a list whose entries are one of:

* a plain string - gear with no armory record yet ("Flashlight");
* a weapon reference - ``{"weapon": <armory record name>, "quantity": 2,
  "note": "Silenced", "label": "Two M7 Silenced Submachine Guns"}``.
  ``quantity`` defaults to 1; ``note`` and ``label`` (the book's wording)
  are optional;
* an armor reference - ``{"armor": <unsc_armor record name>, "label": ...}``;
* a choice group - ``{"label": ..., "choose_one": [reference, ...]}``.
  The player picks one option, the same way upbringing choices work.

A player's picks are stored as option labels (the weapon or armor names),
one per choice group, in pack order. A character wears one armor: if a pack
yields more than one, the first is worn and the rest are carried as gear.
"""

from typing import Dict, List, NamedTuple, Optional, Sequence

ARMORY_FAMILIES = {"unsc_weapons": "unsc_weapons", "unsc_explosives": "unsc_explosives"}
ARMOR_FAMILIES = {"unsc_armor": "unsc_armor"}


def is_weapon_ref(entry) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("weapon"), str)


def is_armor_ref(entry) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("armor"), str)


def is_item_ref(entry) -> bool:
    return is_weapon_ref(entry) or is_armor_ref(entry)


def is_choice(entry) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("choose_one"), list)


def _index(game_data, families) -> Dict[str, dict]:
    index = {}
    for family, key in families.items():
        for doc in (getattr(game_data, "families", {}) or {}).get(family, {}).values():
            for group, records in (doc.get(key) or {}).items():
                for record in records:
                    if isinstance(record, dict) and record.get("name"):
                        index[record["name"]] = {**record, "_family": family, "_group": group}
    return index


def armory_index(game_data) -> Dict[str, dict]:
    """Every weapon and explosive record by name, tagged with where it came from."""
    return _index(game_data, ARMORY_FAMILIES)


def armor_index(game_data) -> Dict[str, dict]:
    """Every UNSC armor record by name."""
    return _index(game_data, ARMOR_FAMILIES)


def option_label(ref: dict) -> str:
    return ref["weapon"] if is_weapon_ref(ref) else ref["armor"]


def weapon_display(ref: dict) -> str:
    """'2x M9 High-Explosive Dual-Purpose Grenade (Silenced)'."""
    quantity = int(ref.get("quantity", 1) or 1)
    text = f"{quantity}x {ref['weapon']}" if quantity > 1 else ref["weapon"]
    return f"{text} ({ref['note']})" if ref.get("note") else text


def describe(entry) -> str:
    """One line for a pack tile, in the book's wording where we have it."""
    if isinstance(entry, str):
        return entry
    if entry.get("label"):
        return entry["label"]
    if is_choice(entry):
        return " or ".join(weapon_display(o) for o in entry["choose_one"])
    if is_weapon_ref(entry):
        return weapon_display(entry)
    if is_armor_ref(entry):
        return entry["armor"]
    return str(entry)


def choice_groups(items: Sequence) -> List[dict]:
    """Choice groups in a pack, shaped for BackgroundChoiceDialog."""
    return [
        {
            "section": "armor" if all(is_armor_ref(o) for o in entry["choose_one"]) else "weapons",
            "row_label": describe(entry),
            "labels": [option_label(o) for o in entry["choose_one"]],
        }
        for entry in items or []
        if is_choice(entry)
    ]


def _weapon_entry(ref: dict, index: Dict[str, dict]) -> dict:
    record = index.get(ref["weapon"], {})
    entry = {"name": ref["weapon"], "quantity": int(ref.get("quantity", 1) or 1)}
    if record.get("nickname"):
        entry["nickname"] = record["nickname"]
    if ref.get("note"):
        entry["note"] = ref["note"]
    if record:
        entry["category"] = record["_group"]
    return entry


class PackContents(NamedTuple):
    weapons: List[dict]
    armor: Optional[str]
    equipment: List[str]
    problems: List[str]


def resolve_pack(
    items: Sequence,
    choices: Optional[Sequence[str]] = None,
    index: Optional[Dict[str, dict]] = None,
    armors: Optional[Dict[str, dict]] = None,
) -> PackContents:
    """Split a pack into weapons, worn armor, carried gear and problems.

    ``weapons`` are ``{"name", "quantity", "nickname", "note", "category"}``
    dicts naming armory records; ``armor`` is a unsc_armor record name. A
    choice group without a valid pick adds nothing and is reported, rather
    than silently choosing for the player.
    """
    index = index or {}
    armors = armors or {}
    picks = list(choices or [])
    weapons, equipment, problems = [], [], []
    worn = None
    group_index = 0
    for entry in items or []:
        if isinstance(entry, str):
            equipment.append(entry)
            continue
        if is_choice(entry):
            options = entry["choose_one"]
            labels = [option_label(o) for o in options]
            pick = picks[group_index] if group_index < len(picks) else None
            group_index += 1
            if pick in labels:
                ref = options[labels.index(pick)]
            else:
                problems.append(f"No valid choice for {describe(entry)} (got {pick!r}); not added")
                continue
        elif is_item_ref(entry):
            ref = entry
        else:
            problems.append(f"Unrecognized pack entry {entry!r}; not added")
            continue
        if is_armor_ref(ref):
            if armors and ref["armor"] not in armors:
                problems.append(f"Unknown armor '{ref['armor']}'")
            if worn is None:
                worn = ref["armor"]
            else:
                equipment.append(f"{ref['armor']} (spare armor)")
            continue
        if index and ref["weapon"] not in index:
            problems.append(f"Unknown armory weapon '{ref['weapon']}'")
        weapons.append(_weapon_entry(ref, index))
    return PackContents(weapons, worn, equipment, problems)


def item_references(items: Sequence) -> List[dict]:
    """Every weapon and armor reference in a pack, including each choice option."""
    refs = []
    for entry in items or []:
        if is_item_ref(entry):
            refs.append(entry)
        elif is_choice(entry):
            refs.extend(o for o in entry["choose_one"] if is_item_ref(o))
    return refs


def weapon_references(items: Sequence) -> List[dict]:
    """Every weapon reference in a pack, including each choice option."""
    return [ref for ref in item_references(items) if is_weapon_ref(ref)]


def armor_summary(name, armors: Optional[Dict[str, dict]] = None) -> str:
    """Sheet line for worn armor: name plus per-location Armor Rating and shields."""
    if not name:
        return ""
    record = (armors or {}).get(name)
    if not record:
        return str(name)
    rating = record.get("armor_rating") or {}
    text = name
    if rating:
        text += " - " + ", ".join(
            f"{loc.title()} {rating[loc]}" for loc in ("head", "arms", "chest", "legs") if loc in rating
        )
    shields = record.get("energy_shields")
    if shields:
        text += (f"; Shields {shields.get('integrity')} "
                 f"(Delay {shields.get('delay')}, Recharge {shields.get('recharge')})")
    return text


def weapon_summary(entry, index: Optional[Dict[str, dict]] = None) -> str:
    """Sheet line for a saved weapon: name, nickname and key stats."""
    if not isinstance(entry, dict):
        return str(entry)
    name = entry.get("name", "")
    quantity = int(entry.get("quantity", 1) or 1)
    text = f"{quantity}x {name}" if quantity > 1 else name
    if entry.get("nickname"):
        text += f" ({entry['nickname']})"
    if entry.get("note"):
        text += f" [{entry['note']}]"
    record = (index or {}).get(name)
    if record:
        damage = record.get("damage")
        bonus = record.get("bonus_damage")
        stats = []
        if damage is not None:
            stats.append(f"{damage}+{bonus}" if bonus not in (None, "") else str(damage))
        if record.get("pierce") is not None:
            stats.append(f"Pierce {record['pierce']}")
        reach_or_range = record.get("range") or record.get("reach")
        if reach_or_range:
            stats.append(str(reach_or_range))
        if record.get("rate_of_fire"):
            stats.append(record["rate_of_fire"])
        if stats:
            text += " - " + ", ".join(stats)
    return text
