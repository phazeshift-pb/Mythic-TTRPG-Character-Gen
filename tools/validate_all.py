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
