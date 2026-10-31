"""Either/or modifiers for upbringings and environments.

The rulebook writes many backgrounds as choices, e.g. City:
"+5 Agility, Courage, or Perception; -5 Strength, Toughness, or Perception".
In the JSON a bonuses/penalties entry is either a plain modifier string that
always applies, or a choice group:

    {"choose_one": ["+5 Agility", "+5 Courage", "+5 Perception"]}

An option may also be a list of modifiers taken together (Laborer:
"+2 Strength and +1 Toughness, or +1 Strength and +2 Toughness").

A player's picks are stored as option labels, one per choice group, in the
order the groups appear (bonuses first, then penalties). Labels are
human-readable, so saved characters stay meaningful if the data is reordered.
"""

from typing import Iterable, List, Optional, Sequence

SECTIONS = ("bonuses", "penalties")


def option_label(option) -> str:
    if isinstance(option, (list, tuple)):
        return " and ".join(str(part) for part in option)
    return str(option)


def option_modifiers(option) -> List[str]:
    return [str(part) for part in option] if isinstance(option, (list, tuple)) else [str(option)]


def is_choice(entry) -> bool:
    return isinstance(entry, dict) and isinstance(entry.get("choose_one"), list)


def choice_groups(record: dict) -> List[dict]:
    """Every choice group in a record: [{'section', 'labels'}] in apply order."""
    groups = []
    for section in SECTIONS:
        for entry in record.get(section, []) or []:
            if is_choice(entry):
                groups.append(
                    {
                        "section": section,
                        "labels": [option_label(o) for o in entry["choose_one"]],
                    }
                )
    return groups


def resolve_modifiers(record: dict, choices: Optional[Sequence[str]] = None):
    """Modifier strings to apply, plus messages for groups left unresolved.

    Returns (modifiers, problems). A group with no valid choice applies
    nothing, rather than silently picking an option for the player.
    """
    picks = list(choices or [])
    modifiers, problems = [], []
    group_index = 0
    for section in SECTIONS:
        for entry in record.get(section, []) or []:
            if not is_choice(entry):
                modifiers.append(str(entry))
                continue
            options = entry["choose_one"]
            labels = [option_label(o) for o in options]
            pick = picks[group_index] if group_index < len(picks) else None
            group_index += 1
            if pick in labels:
                modifiers.extend(option_modifiers(options[labels.index(pick)]))
            else:
                problems.append(
                    f"{record.get('name')}: no valid choice for "
                    f"{' / '.join(labels)} (got {pick!r}); not applied"
                )
    return modifiers, problems


def describe(entries: Iterable) -> List[str]:
    """Display strings for a bonuses/penalties list ('+5 A or +5 B')."""
    return [
        " or ".join(option_label(o) for o in entry["choose_one"]) if is_choice(entry) else str(entry)
        for entry in entries or []
    ]
