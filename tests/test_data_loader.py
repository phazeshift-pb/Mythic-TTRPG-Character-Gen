import json
import os
from collections import Counter

import pytest

from src.data_loader import DataLoader
from src.game_data import GameData
from src.validators.base_validator import BaseValidator
from tools import validate_all


@pytest.mark.parametrize("use_lns", [False, True])
def test_loads_cleanly_and_once(use_lns, monkeypatch):
    counts = Counter()
    original = GameData.add_document

    def counting_add(self, family, name, doc):
        counts[doc["source_path"]] += 1
        original(self, family, name, doc)

    monkeypatch.setattr(GameData, "add_document", counting_add)
    game_data = DataLoader(use_light_and_sky=use_lns).load_all()

    assert game_data.errors == []
    assert counts and max(counts.values()) == 1
    assert game_data.list("soldier_type")


def test_independent_of_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    game_data = DataLoader().load_all()
    assert game_data.errors == []
    assert all(
        doc["source_path"].startswith("data/")
        for family in game_data.families.values()
        for doc in family.values()
    )


def test_duplicate_names_in_a_family_are_reported(tmp_path):
    for folder in ("a", "b"):
        (tmp_path / "core" / folder).mkdir(parents=True)
        (tmp_path / "core" / folder / "skills.json").write_text(json.dumps({"skills": []}))
    game_data = GameData()
    loader = DataLoader(data_root=tmp_path)
    loader._load_folder(loader.core_root, game_data, BaseValidator(game_data))
    assert any("duplicate skills name 'skills'" in e for e in game_data.errors)


def test_skill_characteristics_accept_names_and_codes():
    v = BaseValidator(GameData())
    assert v.characteristic_code("Charisma") == "CHA"
    assert v.characteristic_code("wfm") == "WFM"
    assert v.characteristic_code("Luck") is None


def test_validator_flags_unknown_pack_skill():
    game_data = GameData()
    game_data.add_document(
        "specialization_packs",
        "packs",
        {"specialization_packs": {"standard": [
            {"name": "Bad", "skills": ["Demolitions (Trained)"], "abilities": ["Nope"]}
        ]}},
    )
    errors = []
    validate_all.check_specialization_packs(game_data, {"Demolition"}, set(), errors)
    assert len(errors) == 2


def test_validate_all_passes_on_repo_data(capsys):
    assert validate_all.main([]) == 0


def test_renamed_files_still_feed_the_ui():
    core = DataLoader().load_all()
    assert core.get("encumbrance", "encumbrance") is not None
    assert core.get("perceptive_range", "perceptive_range")["perceptive_range"]["lighting_modifiers"]
    assert core.list("upbringing") and core.list("environment") and core.list("lifestyle")


def test_abilities_have_no_copy_paste_artifacts():
    import re
    from pathlib import Path

    text = (Path(__file__).resolve().parent.parent / "data" / "abilities.json").read_text(encoding="utf-8")
    assert not re.search(r"[+-]\d+o\b", text)  # letter o typed for zero
    abilities = json.loads(text)["abilities"]
    for ability in abilities:
        assert not re.search(r"\s(99|10[0-4])$", ability["description"]), ability["name"]


def test_unsc_armory_loads_in_core_mode():
    core = DataLoader().load_all()
    weapons = core.get("unsc_weapons", "unsc_weapons")["unsc_weapons"]
    explosives = core.get("unsc_explosives", "unsc_grenades_and_explosives")["unsc_explosives"]
    assert sum(map(len, weapons.values())) == 123
    assert sum(map(len, explosives.values())) == 28

    by_name = {w["name"]: w for group in weapons.values() for w in group}
    m6d = by_name["M6D Personal Defense Weapon System"]
    assert (m6d["damage"], m6d["bonus_damage"], m6d["pierce"], m6d["magazine"]) == ("3D10", "10", 4, 12)
    assert m6d["tags"] == ["I", "UD", "OH"] and m6d["special_rules"] == ["Headshot"]
    frag = explosives["grenades"][0]
    assert frag["nickname"] == "Frag Grenade" and frag["range"] == "Blast (8), Kill (2)"

    errors = []
    validate_all.check_unsc_armory(core, errors)
    assert errors == []

    lns = DataLoader(use_light_and_sky=True).load_all()
    assert not lns.list("unsc_weapons")  # core armory is not part of Light & Sky mode


def test_unsc_armory_check_flags_bad_records():
    bad = GameData()
    bad.add_document("unsc_weapons", "w", {"unsc_weapons": {"pistols": [
        {"name": "Gun", "weapon_type": "Pistol", "damage": "3D10", "price": 5, "weight_kg": 1,
         "tags": ["ZZ"], "rate_of_fire": "Auto (1)", "range": "1m-2m", "magazine": 1,
         "magazine_type": "Magazine", "reload": "1 Half Actions", "ammunition": "x"},
        {"name": "Gun", "weapon_type": "Pistol", "damage": "3D10", "price": -1, "weight_kg": 1},
    ]}})
    errors = []
    validate_all.check_unsc_armory(bad, errors)
    assert any("unknown tags" in e for e in errors)
    assert any("duplicate weapon name" in e for e in errors)
    assert any("price must be" in e for e in errors)
    assert any("missing ammunition" in e for e in errors)


def test_lifestyle_and_grenade_checks():
    core = DataLoader().load_all()
    lns = DataLoader(use_light_and_sky=True).load_all()
    errors = []
    validate_all.check_lifestyle_rolls(core, errors)
    validate_all.check_grenades(lns, errors)
    assert errors == []

    bad = GameData()
    bad.add_document("lifestyle", "x", {"lifestyle": [{"name": "Patient", "outcomes": [
        {"roll": "1-6"}, {"roll": "7-10"}, {"roll": "10"}]}]})
    bad.add_document("light_abilities", "y", {"grenades": [
        {"name": "Storm", "pierce": None, "base_damage": "5; second detonation 10"}]})
    errors = []
    validate_all.check_lifestyle_rolls(bad, errors)
    validate_all.check_grenades(bad, errors)
    assert len(errors) == 2


def test_unsc_armor_loads_and_matches_the_book():
    core = DataLoader().load_all()
    armor = core.get("unsc_armor", "unsc_armor")["unsc_armor"]
    by_name = {r["name"]: r for group in armor.values() for r in group}
    assert len(by_name) == 69
    assert by_name["ED4 E.O.D"]["characteristic_bonus"] == {"AGI": -10}
    m52b = by_name["M52B Standard"]
    assert (m52b["weight_kg"], m52b["price"], m52b["armor_rating"]) == (
        11.9, 38, {"head": 18, "arms": 19, "chest": 20, "legs": 19})
    odst = by_name["Standard ODST Battle Dress Uniform"]
    assert "Timeline" in odst["special_rules"] and odst["price"] == 139
    gen3 = by_name["GEN III Powered Armor"]
    assert gen3["energy_shields"] == {"integrity": 175, "delay": 2, "recharge": 50}
    assert gen3["characteristic_bonus"] == {"STR": 20, "mythic_STR": 3, "AGI": 15, "mythic_AGI": 3}
    assert [a["name"] for a in gen3["spartan_abilities"]][:2] == ["Thruster Pack", "Ground Pound"]

    variants = core.get("unsc_armor_variants", "unsc_armor_variants")["mjolnir_variants"]
    assert {g: len(v) for g, v in variants.items()} == {"gen_i": 32, "gen_ii": 73, "gen_iii": 28}
    perms = core.get("unsc_armor_permutations", "unsc_armor_permutations")["armor_permutations"]
    assert sum(map(len, perms.values())) == 95
    cbrn = perms["universal"][0]
    assert (cbrn["name"], cbrn["hardpoints"], cbrn["location"], cbrn["price"]) == ("CBRN", 1, "Universal", 25)

    errors = []
    validate_all.check_unsc_armor(core, errors)
    assert errors == []
