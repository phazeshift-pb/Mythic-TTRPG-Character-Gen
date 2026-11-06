"""Every outlier against the Mythic 7.0 and Light & Sky rules."""
import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models import outliers as rules
from src.models.xp_shop import XpShop


@pytest.fixture(scope="module")
def core_data():
    return DataLoader().load_all()


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


def outlier(data, name):
    return rules.record(data, name)


def marine(data, luck=30):
    character = CharacterGenerator(data).generate("t", "marine", auto_assign_skills=False)
    character.luck_total = character.luck_available = luck
    return character


def test_every_outlier_in_the_book_is_in_the_data(core_data, lns_data):
    core = {
        "Acumen", "Advocate", "Aptitude", "Enduring", "Forte", "Hard-Head", "Imposing",
        "Olympian", "Poised", "Robust", "Rugged", "Strongman", "Vigil", "Vigorous",
    }
    assert {record["name"] for record in rules.records(core_data).values()} == core
    assert {record["name"] for record in rules.records(lns_data).values()} == core | {
        "Passive", "Focus", "Energize", "Super",
    }


@pytest.mark.parametrize("name, times", [("Robust", 2), ("Enduring", 2), ("Vigorous", 2)])
def test_ranked_outliers_can_be_taken_twice_not_three_times(core_data, name, times):
    character = marine(core_data)
    for _ in range(times + 1):
        character.apply_outlier(outlier(core_data, name), 1)
    assert character.outliers.count(name) == times
    assert character.luck_total == 30 - times  # the refused take burns nothing


def test_single_outliers_are_taken_once(core_data):
    character = marine(core_data)
    for _ in range(2):
        character.apply_outlier(outlier(core_data, "Vigil"), 1)
    assert character.outliers == ["Vigil"]


def test_aptitude_twice_per_characteristic(core_data):
    character = marine(core_data)
    base = dict(character.characteristics)
    for code in ("STR", "STR", "STR", "AGI"):
        character.apply_outlier(outlier(core_data, "Aptitude"), 1, code)
    assert character.characteristics["STR"] == base["STR"] + 10
    assert character.characteristics["AGI"] == base["AGI"] + 5
    assert character.outlier_choices == {"Aptitude": ["STR", "STR", "AGI"]}
    assert character.outliers.count("Aptitude") == 3


def test_forte_twice_per_mythic(core_data):
    character = marine(core_data)
    for code in ("TOU", "TOU", "TOU"):
        character.apply_outlier(outlier(core_data, "Forte"), 1, code)
    assert character.mythic_characteristics["TOU"] == "+2"
    with pytest.raises(ValueError):
        character.apply_outlier(outlier(core_data, "Forte"), 1, "INT")


def test_robust_twice_adds_36_wounds(core_data):
    character = marine(core_data)
    before = character.wounds
    character.apply_outlier(outlier(core_data, "Robust"), 1)
    character.apply_outlier(outlier(core_data, "Robust"), 1)
    assert character.wounds == before + 36


def test_imposing_adds_strength_and_toughness(core_data):
    character = marine(core_data)
    base = dict(character.characteristics)
    character.apply_outlier(outlier(core_data, "Imposing"), 1)
    assert character.characteristics["STR"] == base["STR"] + 3
    assert character.characteristics["TOU"] == base["TOU"] + 3


def test_advocate_support_points_and_clearing(core_data):
    character = marine(core_data)
    character.apply_outlier(outlier(core_data, "Advocate"), 1)
    assert character.support_points == 2
    character.clear_outliers(rules.records(core_data) | {"Advocate": outlier(core_data, "Advocate")})
    assert character.support_points == 0 and character.outliers == []


def test_acumen_triples_education_and_language_limits(core_data):
    character = {"characteristics": {"INT": 40}, "outliers": []}
    shop = XpShop(character, core_data, "Core")
    assert (shop.education_limit(), shop.language_limit()) == (8, 4)
    character["outliers"] = ["Acumen"]
    shop = XpShop(character, core_data, "Core")
    assert (shop.education_limit(), shop.language_limit()) == (24, 12)


def test_enduring_and_vigorous_ranks(core_data):
    assert rules.ignored_fatigue_levels(core_data, {"outliers": ["Enduring"]}) == 2
    assert rules.ignored_fatigue_levels(core_data, {"outliers": ["Enduring", "Enduring"]}) == 4
    assert rules.natural_healing_multiplier(core_data, {"outliers": []}) == 1
    assert rules.natural_healing_multiplier(core_data, {"outliers": ["Vigorous"]}) == 2
    assert rules.natural_healing_multiplier(core_data, {"outliers": ["Vigorous"] * 2}) == 3
    summary = rules.summary(core_data, {"outliers": ["Vigorous", "Vigorous"]})
    assert summary == [{"name": "Vigorous", "times": 2, "picks": [], "effect": "Triple Natural Healing."}]


def test_wounds_rules_are_loaded_for_the_sheet(core_data, lns_data):
    for data in (core_data, lns_data):
        assert data.get("wounds", "wounds")["wounds"]["fatigue"]["penalty_per_level"] == -5


def test_guardian_outliers_are_once_each(lns_data):
    for name in ("Passive", "Focus", "Energize", "Super"):
        assert rules.max_times(outlier(lns_data, name)) == 1
        assert rules.needs_choice(outlier(lns_data, name)) is None
