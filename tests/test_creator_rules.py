"""Character creator rules checked against Mythic 7.0 CU1 and Light and Sky.

Each test names the book rule it covers (see the creator audit doc).
"""
import random

import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.character import BackgroundFloorError, Character
from src.models.xp_shop import XpShop


@pytest.fixture(scope="module")
def core_data():
    return DataLoader().load_all()


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


def core(data, soldier, xp=20000, **kwargs):
    return CharacterGenerator(data).generate(
        "t", soldier, auto_assign_skills=False, starting_experience=xp, **kwargs
    )


def guardian(data, guardian_class, subclass, seed=1):
    return CharacterGenerator(data, use_light_and_sky=True, rng=random.Random(seed)).generate(
        "G", guardian_class, subclass=subclass, human_soldier_type="human_awoken",
        guardian_class=guardian_class, auto_assign_skills=False, starting_experience=15000,
    )


def test_smart_ai_matches_the_book(core_data):
    record = core_data.get("soldier_type", "smart_ai")
    assert record["experience_cost"] == 5050
    assert record["training"] == ["All"] and record["upbringing"] == "Any"
    assert record["base_characteristics"] == {
        "STR": 25, "TOU": 25, "AGI": 25, "WFR": 40, "WFM": 25,
        "INT": 50, "PER": 50, "CRG": 35, "CHA": 35, "LDR": 35,
    }
    assert record["special_rules"]["no_specialization_pack"] is True
    character = core(core_data, "smart_ai")
    assert character.experience == 20000 - 5050


def test_smart_ai_skill_training_is_four_at_plus_ten(core_data):
    pytest.importorskip("PySide6")
    from src.ui.creator.initial_setup import InitialSetupMixin

    record = core_data.get("soldier_type", "smart_ai")
    assert InitialSetupMixin._skill_training_requirements(record) == (4, 10)


def test_navy_technician_costs_1550(core_data):
    assert core_data.get("soldier_type", "navy_technician")["experience_cost"] == 1550


@pytest.mark.parametrize(
    "guardian_class, subclass, expected",
    [
        ("titan", "Defender", {"TOU": 10, "STR": -5, "AGI": -5}),
        ("titan", "Striker", {"WFM": 10, "WFR": -10}),
        ("hunter", "Bladedancer", {"WFM": 10, "WFR": -10}),
    ],
)
def test_subclass_modifiers(lns_data, guardian_class, subclass, expected):
    record = lns_data.get("soldier_type", guardian_class)["subclasses"][subclass]
    modifiers = {code: int(value) for code, value in record["characteristic_modifiers"].items()}
    assert modifiers == expected


@pytest.mark.parametrize("xp, credits", [(500, 50), (2500, 350), (15000, 800), (70000, 1450)])
def test_starting_credits_follow_the_experience_tier(core_data, xp, credits):
    assert core(core_data, "marine", xp=xp).credits == credits


def test_spartan_trait_abilities_rank_and_faction_training(core_data):
    spartan_ii = core(core_data, "spartan_ii")
    assert {"Emotionally Broken", "Fast Foot"} <= set(spartan_ii.abilities)
    assert spartan_ii.rank == "Petty Officer Second Class"
    for soldier in ("spartan_iii", "spartan_iv"):
        assert "Fast Foot" in core(core_data, soldier).abilities
    export = {"soldier_type": spartan_ii.soldier_type, "characteristics": spartan_ii.characteristics}
    shop = XpShop(export, core_data, "Core")
    assert {"UNSC", "Covenant", "Forerunner"} <= shop.owned_faction_training()
    marine = core(core_data, "marine")
    assert XpShop({"soldier_type": marine.soldier_type}, core_data, "Core").owned_faction_training() == {"UNSC"}


def test_oni_rank_and_support_point(core_data):
    oni = core(core_data, "oni_section_i")
    assert oni.rank == "O-1"
    assert oni.support_points == 1


def test_starting_educations_and_smart_ai_has_no_education_limit(core_data):
    navy = core(core_data, "navy_technician", starting_educations={"Aeronautics": 5, "Agriculture": 5})
    assert navy.educations == {"Aeronautics": 5, "Agriculture": 5}
    with pytest.raises(ValueError):
        core(core_data, "navy_technician", starting_educations={"Aeronautics": 7})
    ai = core(core_data, "smart_ai")
    shop = XpShop({"soldier_type": ai.soldier_type, "characteristics": ai.characteristics}, core_data, "Core")
    assert shop.education_limit() >= 1000
    assert core_data.get("soldier_type", "navy_technician")["special_rules"]["starting_educations"] == {
        "count": 3, "level": 5,
    }


@pytest.mark.parametrize("guardian_class, subclass", [("titan", "Sentinel"), ("hunter", "Revenant"), ("warlock", "Voidwalker")])
def test_guardians_decode_three_weapon_and_one_armor_engram(lns_data, guardian_class, subclass):
    character = guardian(lns_data, guardian_class, subclass)
    assert len(character.weapons) == 3
    assert all(weapon["loot"]["rarity"] == "Common" for weapon in character.weapons)
    assert character.armor_loot and character.armor_loot["rarity"] == "Common"
    assert character.armor.startswith("Common")
    assert character.armor_equipped


def test_starting_connections_are_light_only(lns_data):
    light = [entry["name"] for entry in lns_data.get("connections", "connections")["connections"]["light"]]
    assert light == ["Arc", "Solar", "Void"]


def test_background_cant_lower_a_characteristic_to_five_or_below():
    character = Character()
    character.characteristics["CHA"] = 10
    character.characteristics["TOU"] = 25
    with pytest.raises(BackgroundFloorError):
        character._apply_background({"name": "Test", "penalties": ["-5 Charisma"]})
    assert character.characteristics["CHA"] == 10  # nothing applied
    character._apply_background({"name": "Test", "penalties": ["-3 Charisma"]})
    assert character.characteristics["CHA"] == 7


def test_upbringing_limits_by_soldier_type(core_data):
    pytest.importorskip("PySide6")
    from src.ui.creator.initial_setup import InitialSetupMixin

    class Combo:
        def __init__(self, key):
            self.key = key

        def currentData(self):
            return self.key

    setup = InitialSetupMixin()
    setup.game_data = core_data
    setup.soldier_combo = Combo("spartan_iii")
    assert setup._allowed_upbringings() == {"military", "war orphan"}
    assert setup._upbringing_key("War Orphan") in setup._allowed_upbringings()
    setup.soldier_combo = Combo("marine")
    assert setup._allowed_upbringings() is None
