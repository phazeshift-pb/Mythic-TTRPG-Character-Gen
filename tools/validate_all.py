"""Validate every rules file and saved character.

Usage (from anywhere):
    python tools/validate_all.py            # errors + warnings
    python tools/validate_all.py --verbose  # also list data files no mode loads

Exits with status 1 if any error is found, so it can run in CI or a
pre-commit hook. Warnings (stale saved characters, unloaded files) never
fail the run.
"""

import argparse
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from src.data_loader import DataLoader  # noqa: E402
from src.models.background_choices import SECTIONS, is_choice, option_modifiers  # noqa: E402
from src.models.character import CHARACTERISTIC_NAME_TO_CODE  # noqa: E402
from src.models import equipment_packs, starting_armor  # noqa: E402
from src.validators.base_validator import BaseValidator  # noqa: E402

DATA_ROOT = REPO_ROOT / "data"
CHARACTERS_ROOT = REPO_ROOT / "characters"
_TRAINING_SUFFIX = re.compile(r"\s*\((?:Trained|\+\d+)\)\s*$")


def _names(doc, key):
    return {
        entry["name"]
        for entry in (doc or {}).get(key, [])
        if isinstance(entry, dict) and "name" in entry
    }


def _base_skill(name):
    """'Pilot (Air) (Trained)' -> 'Pilot (Air)'; 'Pilot (Air)' -> 'Pilot'."""
    stripped = _TRAINING_SUFFIX.sub("", name)
    return stripped, re.sub(r"\s*\(.*\)$", "", stripped)


def check_json_syntax(errors):
    for path in sorted(DATA_ROOT.rglob("*.json")):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            errors.append(f"{path.relative_to(REPO_ROOT).as_posix()}: invalid JSON: {exc}")


def check_specialization_packs(game_data, known_skills, known_abilities, errors):
    for doc in game_data.families.get("specialization_packs", {}).values():
        packs = doc.get("specialization_packs", {})
        source = doc.get("source_path", "specialization_packs")
        for group in ("standard", "limited"):
            for pack in packs.get(group, []):
                for skill in pack.get("skills", []):
                    full, base = _base_skill(skill)
                    if full not in known_skills and base not in known_skills:
                        errors.append(
                            f"{source}: pack '{pack.get('name')}' grants unknown skill '{skill}'"
                        )
                for ability in pack.get("abilities", []):
                    if ability not in known_abilities:
                        errors.append(
                            f"{source}: pack '{pack.get('name')}' grants unknown ability '{ability}'"
                        )


def _roll_range(text):
    low, _, high = str(text).partition("-")
    return int(low), int(high or low)


def check_lifestyle_rolls(game_data, errors):
    """Lifestyle outcomes must cover 1-10 exactly once."""
    for doc in game_data.families.get("lifestyle", {}).values():
        source = doc.get("source_path", "lifestyle")
        for lifestyle in doc.get("lifestyle", []):
            covered = []
            try:
                for outcome in lifestyle.get("outcomes", []):
                    low, high = _roll_range(outcome["roll"])
                    covered.extend(range(low, high + 1))
            except (KeyError, ValueError):
                errors.append(f"{source}: lifestyle '{lifestyle.get('name')}' has an unreadable roll range")
                continue
            if sorted(covered) != list(range(1, 11)):
                errors.append(
                    f"{source}: lifestyle '{lifestyle.get('name')}' rolls do not cover 1-10 "
                    f"exactly once (got {sorted(covered)})"
                )


def check_grenades(game_data, errors):
    """Grenade stat fields hold one value each; extra detonations get their own object."""
    for doc in game_data.families.get("light_abilities", {}).values():
        source = doc.get("source_path", "light_abilities")
        for grenade in doc.get("grenades", []):
            for stats in (grenade, grenade.get("second_detonation") or {}):
                pierce = stats.get("pierce")
                if pierce is not None and not isinstance(pierce, int):
                    errors.append(f"{source}: grenade '{grenade.get('name')}' pierce must be a number")
                for field in ("base_damage", "damage_roll", "range"):
                    if ";" in str(stats.get(field) or ""):
                        errors.append(
                            f"{source}: grenade '{grenade.get('name')}' {field} mixes several values"
                        )


WEAPON_TAGS = {"I", "U", "UD", "OH", "TH", "DW", "HW", "PD", "SD", "BD"}
RANGED_FIELDS = ("rate_of_fire", "range", "magazine", "magazine_type", "reload", "ammunition")


def check_unsc_armory(game_data, errors):
    """Core UNSC weapons and explosives: unique names, known tags, sane numbers."""
    for family, key in (("unsc_weapons", "unsc_weapons"), ("unsc_explosives", "unsc_explosives")):
        for doc in game_data.families.get(family, {}).values():
            source = doc.get("source_path", family)
            seen = set()
            for group, records in doc.get(key, {}).items():
                for record in records:
                    name = record.get("name")
                    if not name:
                        errors.append(f"{source}: {group} entry missing name")
                        continue
                    if name in seen:
                        errors.append(f"{source}: duplicate weapon name '{name}'")
                    seen.add(name)
                    for field in ("weapon_type", "damage", "price", "weight_kg"):
                        if field not in record:
                            errors.append(f"{source}: '{name}' missing {field}")
                    for field in ("price", "weight_kg"):
                        value = record.get(field)
                        if not isinstance(value, (int, float)) or value < 0:
                            errors.append(f"{source}: '{name}' {field} must be a non-negative number")
                    unknown = set(record.get("tags", [])) - WEAPON_TAGS
                    if unknown:
                        errors.append(f"{source}: '{name}' has unknown tags {sorted(unknown)}")
                    if family == "unsc_weapons" and group != "melee_weapons":
                        for field in RANGED_FIELDS:
                            if record.get(field) in (None, ""):
                                errors.append(f"{source}: '{name}' missing {field}")
                    pierce = record.get("pierce")
                    if pierce is not None and not isinstance(pierce, (int, str)):
                        errors.append(f"{source}: '{name}' pierce must be a number or formula text")


ARMOR_LOCATIONS = ("head", "arms", "chest", "legs")
CHARACTERISTIC_CODES = BaseValidator.CHARACTERISTIC_CODES
PERMUTATION_LOCATIONS = {"Universal", "Head", "Chest", "Arm", "Each Arm", "Leg", "Each Leg", "All"}


def check_unsc_armor(game_data, errors):
    """Armor ratings, prices, unique names; variants and permutations well formed."""
    for doc in game_data.families.get("unsc_armor", {}).values():
        source = doc.get("source_path", "unsc_armor")
        seen = set()
        for group, records in doc.get("unsc_armor", {}).items():
            for record in records:
                name = record.get("name")
                if name in seen:
                    errors.append(f"{source}: duplicate armor name '{name}'")
                seen.add(name)
                rating = record.get("armor_rating") or {}
                if set(rating) != set(ARMOR_LOCATIONS) or not all(
                    isinstance(v, int) and v >= 0 for v in rating.values()
                ):
                    errors.append(f"{source}: '{name}' needs a whole-number armor_rating for {ARMOR_LOCATIONS}")
                price = record.get("price")
                if price is not None and (not isinstance(price, int) or price < 0):
                    errors.append(f"{source}: '{name}' price must be a non-negative whole number or null")
                if not isinstance(record.get("weight_kg"), (int, float)):
                    errors.append(f"{source}: '{name}' weight_kg must be a number")
                if record.get("armor_type") not in ("Standard", "Semi-Powered", "Powered"):
                    errors.append(f"{source}: '{name}' has unknown armor_type {record.get('armor_type')!r}")
    for doc in game_data.families.get("unsc_armor_variants", {}).values():
        source = doc.get("source_path", "unsc_armor_variants")
        for generation, records in doc.get("mjolnir_variants", {}).items():
            names = [r.get("name") for r in records]
            for name in {n for n in names if names.count(n) > 1}:
                errors.append(f"{source}: duplicate {generation} variant '{name}'")
            for record in records:
                if not isinstance(record.get("price"), int) or record["price"] < 0:
                    errors.append(f"{source}: variant '{record.get('name')}' price must be a non-negative whole number")
    for doc in game_data.families.get("unsc_armor_permutations", {}).values():
        source = doc.get("source_path", "unsc_armor_permutations")
        for section, records in doc.get("armor_permutations", {}).items():
            names = [r.get("name") for r in records]
            for name in {n for n in names if names.count(n) > 1}:
                errors.append(f"{source}: duplicate {section} permutation '{name}'")
            for record in records:
                if record.get("location") not in PERMUTATION_LOCATIONS:
                    errors.append(f"{source}: permutation '{record.get('name')}' has unknown location")
                if not isinstance(record.get("hardpoints"), int) or record["hardpoints"] < 0:
                    errors.append(f"{source}: permutation '{record.get('name')}' hardpoints must be a whole number")


def check_starting_armor_options(game_data, errors):
    """Spartan starting-armor options and worn bonuses must name real armor."""
    armors = equipment_packs.armor_index(game_data)
    if not armors:
        return
    for name, doc in game_data.families.get("soldier_type", {}).items():
        source = doc.get("source_path", name)
        rules = starting_armor.armor_rules(doc)
        for option in rules.get("armor_options", []):
            if not isinstance(option, dict) or option.get("armor") not in armors:
                errors.append(f"{source}: starting armor option {option!r} does not name a unsc_armor record")
        extra = rules.get("bonus_while_worn") or {}
        for armor in extra.get("armor", []):
            if armor not in armors:
                errors.append(f"{source}: bonus_while_worn names unknown armor '{armor}'")
        for code in (extra.get("characteristics") or {}):
            if code not in CHARACTERISTIC_CODES:
                errors.append(f"{source}: bonus_while_worn has unknown characteristic '{code}'")


def check_equipment_packs(game_data, errors):
    """Pack references must name armory/armor records; choices need 2+ options."""
    index = equipment_packs.armory_index(game_data)
    armors = equipment_packs.armor_index(game_data)
    if not index:
        return  # this ruleset has no armory (Light & Sky packs are plain text)
    for name, doc in game_data.families.get("soldier_type", {}).items():
        source = doc.get("source_path", name)
        for pack, items in (doc.get("equipment_sets") or {}).items():
            for entry in items:
                if isinstance(entry, str):
                    continue
                if equipment_packs.is_choice(entry):
                    options = entry["choose_one"]
                    if len(options) < 2 or not all(equipment_packs.is_item_ref(o) for o in options):
                        errors.append(
                            f"{source}: pack '{pack}' has a malformed choice group "
                            f"'{equipment_packs.describe(entry)}' (need 2+ weapon or armor options)"
                        )
                        continue
                elif not equipment_packs.is_item_ref(entry):
                    errors.append(f"{source}: pack '{pack}' has an unrecognized entry {entry!r}")
                    continue
                for ref in equipment_packs.item_references([entry]):
                    if equipment_packs.is_armor_ref(ref):
                        if ref["armor"] not in armors:
                            errors.append(
                                f"{source}: pack '{pack}' references unknown armor '{ref['armor']}'"
                            )
                        continue
                    if ref["weapon"] not in index:
                        errors.append(
                            f"{source}: pack '{pack}' references unknown weapon '{ref['weapon']}'"
                        )
                    quantity = ref.get("quantity", 1)
                    if not isinstance(quantity, int) or quantity < 1:
                        errors.append(
                            f"{source}: pack '{pack}' weapon '{ref['weapon']}' quantity must be a positive whole number"
                        )


_MODIFIER = re.compile(r"^\s*[+-]\d+\s+(.+?)\s*$")


def _modifier_target_ok(text):
    match = _MODIFIER.match(str(text))
    if not match:
        return False
    target = match.group(1).casefold()
    return target == "wounds" or target in CHARACTERISTIC_NAME_TO_CODE


def check_background_modifiers(game_data, errors, warnings):
    """Choice groups must be well formed; every modifier must be one the app applies."""
    for family in ("upbringing", "environment", "lifestyle"):
        for doc in game_data.families.get(family, {}).values():
            source = doc.get("source_path", family)
            for record in doc.get(family, []):
                holders = record.get("outcomes") or [record]
                for holder in holders:
                    for section in SECTIONS:
                        for entry in holder.get(section, []) or []:
                            if isinstance(entry, dict):
                                if not is_choice(entry) or len(entry["choose_one"]) < 2:
                                    errors.append(
                                        f"{source}: {record.get('name')} has a malformed choice "
                                        f"group in {section} (need choose_one with 2+ options)"
                                    )
                                    continue
                                texts = [m for o in entry["choose_one"] for m in option_modifiers(o)]
                            else:
                                texts = [entry]
                            for text in texts:
                                if not _modifier_target_ok(text):
                                    warnings.append(
                                        f"{source}: {record.get('name')} modifier '{text}' "
                                        "is not applied automatically"
                                    )


def check_saved_characters(known_skills, known_abilities, warnings):
    for path in sorted(CHARACTERS_ROOT.glob("*.json")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        try:
            export = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            warnings.append(f"{rel}: invalid JSON: {exc}")
            continue
        if export.get("format_version") != 1 or "character" not in export:
            warnings.append(f"{rel}: not a format_version 1 character export")
            continue
        character = export["character"]
        for skill in character.get("skills", {}):
            full, base = _base_skill(skill)
            if full not in known_skills and base not in known_skills:
                warnings.append(f"{rel}: unknown skill '{skill}' (regenerate or edit)")
        for ability in character.get("abilities", []):
            if ability not in known_abilities:
                warnings.append(f"{rel}: unknown ability '{ability}'")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)

    errors, warnings = [], []
    check_json_syntax(errors)

    loaded = set()
    known_skills, known_abilities = set(), set()
    for use_lns, label in ((False, "Core"), (True, "Light & Sky")):
        loader = DataLoader(use_light_and_sky=use_lns)
        game_data = loader.load_all()
        errors.extend(f"[{label}] {message}" for message in game_data.errors)
        loaded |= loader._loaded_paths

        for doc in game_data.families.get("skills", {}).values():
            known_skills |= _names(doc, "skills")
        for doc in game_data.families.get("light_abilities", {}).values():
            known_abilities |= _names(doc, "abilities")
        check_specialization_packs(game_data, known_skills, known_abilities, errors)
        check_lifestyle_rolls(game_data, errors)
        check_background_modifiers(game_data, errors, warnings)
        check_grenades(game_data, errors)
        check_unsc_armory(game_data, errors)
        check_unsc_armor(game_data, errors)
        check_equipment_packs(game_data, errors)
        check_starting_armor_options(game_data, errors)

    check_saved_characters(known_skills, known_abilities, warnings)

    if args.verbose:
        unloaded = sorted(
            p.relative_to(REPO_ROOT).as_posix()
            for p in DATA_ROOT.rglob("*.json")
            if p.resolve() not in loaded
        )
        print(f"Data files not loaded by either mode ({len(unloaded)}):")
        for path in unloaded:
            print(f"  - {path}")
        print()

    errors = list(dict.fromkeys(errors))  # same issue can appear in both modes
    warnings = list(dict.fromkeys(warnings))
    for message in warnings:
        print(f"WARNING: {message}")
    for message in errors:
        print(f"ERROR: {message}")
    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
