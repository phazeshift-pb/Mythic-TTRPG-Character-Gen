"""Light and Sky: Sub-Classes can be changed between missions, refunding their benefits."""
import random

import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models import subclass as rules


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


def titan(data, subclass="Defender"):
    from dataclasses import asdict

    character = CharacterGenerator(data, use_light_and_sky=True, rng=random.Random(1)).generate(
        "T", "titan", subclass=subclass, human_soldier_type="human_awoken",
        guardian_class="titan", auto_assign_skills=False, starting_experience=15000,
    )
    export = asdict(character)
    export.pop("debug_log")
    return export


def test_new_guardians_record_their_subclass(lns_data):
    assert titan(lns_data)["subclass"] == "Defender"
    assert rules.subclass_names(lns_data, titan(lns_data)) == [
        "Defender", "Sentinel", "Striker", "Sunbreaker", "Behemoth",
    ]


def test_changing_subclass_refunds_the_old_one_and_applies_the_new(lns_data):
    defender = titan(lns_data, "Defender")  # +10 TOU, -5 STR, -5 AGI
    striker = titan(lns_data, "Striker")  # +10 WFM, -10 WFR
    change = rules.change_subclass(lns_data, defender, "Striker")
    assert change == {"AGI": 5, "STR": 5, "TOU": -10, "WFM": 10, "WFR": -10}
    assert defender["characteristics"] == striker["characteristics"]
    assert defender["subclass"] == "Striker"
    # back again lands exactly where it started
    rules.change_subclass(lns_data, defender, "Defender")
    assert defender["characteristics"] == titan(lns_data, "Defender")["characteristics"]


def test_wounds_follow_max_wounds(lns_data):
    character = titan(lns_data, "Striker")
    full = character["wounds"]
    rules.change_subclass(lns_data, character, "Behemoth")  # +10 TOU: +2 Max Wounds
    assert character["wounds"] == full + 2
    rules.change_subclass(lns_data, character, "Striker")
    assert character["wounds"] == full


def test_unrecorded_subclass_is_only_recorded(lns_data):
    character = titan(lns_data, "Sentinel")
    character["subclass"] = None
    before = dict(character["characteristics"])
    assert rules.change_subclass(lns_data, character, "Sentinel") == {}
    assert character["characteristics"] == before and character["subclass"] == "Sentinel"
    with pytest.raises(ValueError):
        rules.change_subclass(lns_data, character, "Gunslinger")  # a Hunter sub-class
