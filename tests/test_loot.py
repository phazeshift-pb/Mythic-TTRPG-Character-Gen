"""Light & Sky loot generator: rolls, and putting loot on a character."""
import json
import random

import pytest

from src.data_loader import DataLoader
from src.loot import character_loot
from src.loot.generator import (
    ARMOR_MATERIALS,
    WEAPON_TYPES,
    LootDataMissing,
    LootGenerator,
)
from src.loot.loot_rules import PERK_COUNTS, RARITIES
from src.models import worn_armor
from src.models.equipment_packs import weapon_summary


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


@pytest.fixture
def generator(lns_data):
    return LootGenerator(lns_data, rng=random.Random(1234))


def test_every_weapon_type_has_models(generator):
    for label, key, _ in WEAPON_TYPES:
        assert generator.weapon_tables[key], label
        roll = generator.generate_weapon(key)
        assert roll["weapon_type"] == label


def test_core_data_has_no_loot():
    with pytest.raises(LootDataMissing):
        LootGenerator(DataLoader(use_light_and_sky=False).load_all())


@pytest.mark.parametrize("rarity", RARITIES)
def test_forced_rarity_sets_perk_counts(generator, rarity):
    for _ in range(20):
        for roll in (
            generator.generate_weapon(forced_rarity=rarity),
            generator.generate_armor(forced_rarity=rarity),
        ):
            if roll["rarity"] == "Exotic":  # the exotic chance can upgrade any roll
                assert roll["exotic_perk"]["name"]
            else:
                assert roll["rarity"] == rarity and roll["exotic_perk"] is None
            minimum, maximum = PERK_COUNTS[roll["rarity"]]
            assert minimum <= len(roll["perks"]) <= maximum
            assert len({p["name"] for p in roll["perks"]}) == len(roll["perks"])


def test_ammo_filter(generator):
    available = generator.weapon_types("Heavy")
    assert available and len(available) < len(WEAPON_TYPES)
    for _ in range(30):
        assert generator.generate_weapon(ammo_type="Heavy")["ammo_type"] == "Heavy"
    with pytest.raises(ValueError):
        generator.generate_weapon("hand_cannon", ammo_type="Heavy")


def test_armor_modifiers(generator):
    base = {"weight_kg": "18.5", "armor": {"head": "20", "arms": "21", "chest": "22", "legs": "21"}}
    subtype = {"name": "Dense Plating", "armor_variant_modifiers": {"agility": -10}}
    variant = {"name": "Super Heavy", "weight_modifier": 8, "armor_modifier": 3,
               "additional_modifiers": {"agility": -10}}
    modified = generator.apply_armor_modifiers(base, subtype, variant)
    assert modified == {
        "weight": "26.5",
        "armor_values": {"head": 23, "arms": 24, "chest": 25, "legs": 24},
        "agility_modifier": -20,
    }
    # "Player's Choice" has no weight/armor modifier.
    choice = {"name": "Player's Choice", "weight_modifier": None, "armor_modifier": None}
    assert generator.apply_armor_modifiers(base, subtype, choice)["weight"] == "18.5"
    for material in ARMOR_MATERIALS:
        assert generator.generate_armor(material)["material"] == material.title()


def test_rolls_are_json_ready(generator):
    json.dumps([generator.generate_weapon(), generator.generate_armor()])


def test_add_weapon_to_character(generator):
    character = {"weapons": [{"name": "M6D Pistol"}]}
    roll = generator.generate_weapon("hand_cannon", forced_rarity="Legendary")
    entry = character_loot.add_weapon(character, roll)
    assert character["weapons"][-1] is entry
    assert entry["source"] == character_loot.LOOT_SOURCE
    summary = weapon_summary(entry)
    assert summary.startswith(f"Legendary {roll['element']} Hand Cannon - {roll['damage']}+")
    assert "Perks: " in summary


def test_equip_armor_applies_agility(generator, lns_data):
    roll = generator.generate_armor("plasteel", forced_rarity="Rare")
    roll["agility_modifier"] = -10
    character = {"characteristics": {"AGI": 40}, "armor": "Old Armor", "armor_equipped": False}
    name = character_loot.equip_armor(character, roll)
    assert character["armor"] == name == "Rare Plasteel Armor Set"
    assert character_loot.worn_loot_armor(character) == roll
    assert worn_armor.is_equipped(character)
    effective = worn_armor.effective_character(character)
    assert effective["characteristics"]["AGI"] == 30
    assert character_loot.armor_sheet_lines(roll)[0].startswith("Rare Plasteel Armor Set - Head ")


def test_loot_card_html(generator):
    weapon = generator.generate_weapon(forced_rarity="Exotic")
    html = character_loot.loot_card_html(weapon)
    assert "EXOTIC" in html and "Exotic Perk:" in html and "LIGHT &amp; SKY" in html
    assert character_loot.element_icon(weapon["element"]) in html
    armor_html = character_loot.loot_card_html(generator.generate_armor("hadronic"))
    assert "Hadronic Armor Set" in armor_html
