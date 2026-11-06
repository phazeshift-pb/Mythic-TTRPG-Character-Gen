import json
from pathlib import Path

import pytest

from src.models import damage_resistance as dr

DATA = Path(__file__).resolve().parent.parent / "data" / "core" / "equipment"

ARMORS = {
    "Mark VI Powered Assault Armor": {"armor_rating": {"head": 27, "arms": 28, "chest": 28, "legs": 26}},
}


@pytest.mark.parametrize("text,expected", [
    ("giving -1 Armor to the Chest location and Head location.", {"head": -1, "chest": -1}),
    ("offers the Character a +1 Armor to Chest and a +5 to Perception Tests.", {"chest": 1}),
    ("Deadeye has -4 to all Armor Locations.", {s: -4 for s in dr.SLOTS}),
    ("The suit's up-armored Helmet gains +4 Armor due to being enclosed.", {"head": 4}),
    ("The Arms, Legs, and Chest Armor Location gains a +3 Bonus.", {"chest": 3, "arms": 3, "legs": 3}),
    ("The suit gives the user +2 Mythic Agility, while suffering a Penalty of -2 Armor to all Locations.",
     {s: -2 for s in dr.SLOTS}),
    ("The suit suffers a -2 to armor in the Arms, Torso, and Legs Locations.", {"chest": -2, "arms": -2, "legs": -2}),
    ("CQB/CQC gains +10 Armor against Melee Attacks and gains +3 Armor against projectile attacks.", {}),
    ("Dynast features the Close-Combat Automatic Interface (CCAI) and a +6 Armor to all Locations.",
     {s: 6 for s in dr.SLOTS}),
    ("Recon's increased Shields of +20 Shield Integrity also gives the suit a -2 Penalty to Armor on all Locations.",
     {s: -2 for s in dr.SLOTS}),
    ("The Stalker suit gains a -1 Penalty to armor on the Arms, Legs, and Helmet Locations, "
     "while gaining a -3 Penalty to armor on the Chest Location.", {"head": -1, "arms": -1, "legs": -1, "chest": -3}),
    ("Smart and Dumb AI housed within the Armor will gain a +10 Bonus to any Armor Interface Abilities they use.", {}),
])
def test_variant_armor_modifiers(text, expected):
    assert dr.variant_armor_modifiers(text) == expected


def test_every_variant_parses_to_small_whole_numbers():
    variants = json.loads((DATA / "unsc_armor_variants.json").read_text(encoding="utf-8"))["mjolnir_variants"]
    for table in variants.values():
        for variant in table:
            for value in dr.variant_armor_modifiers(variant.get("description")).values():
                assert -10 <= value <= 10, variant["name"]


def spartan(**extra):
    character = {
        "characteristics": {"TOU": 60}, "mythic_characteristics": {"TOU": "+4"},
        "armor": "Mark VI Powered Assault Armor", "armor_equipped": True,
    }
    character.update(extra)
    return character


def test_totals_add_armor_toughness_and_mythic():
    c = spartan()
    table = dr.damage_resistance(60, "+4", dr.armor_ratings(c, ARMORS))
    assert table["head"] == {"armor": 27, "variant": 0, "toughness": 6, "mythic": 4, "other": 0, "total": 37}
    assert table["legs"]["total"] == 26 + 10


def test_unequipped_armor_counts_as_zero():
    c = spartan(armor_equipped=False)
    assert dr.damage_resistance(60, "+4", dr.armor_ratings(c, ARMORS))["chest"]["total"] == 10


def test_variant_and_other_adjustments():
    c = spartan(armor_variant={"name": "Aviator", "generation": "GEN I",
                               "description": "giving -1 Armor to the Chest location and Head location."})
    table = dr.damage_resistance(60, 4, dr.armor_ratings(c, ARMORS), other={"arms": 2})
    assert table["chest"]["total"] == 28 - 1 + 10
    assert table["arms"]["total"] == 28 + 2 + 10


def test_loot_armor_values_and_no_armor():
    loot = {"rarity": "Rare", "material": "Plasteel", "armor_values": {"head": 20, "arms": 21, "chest": 22, "legs": 21}}
    c = {"armor": "Rare Plasteel Armor Set", "armor_loot": loot, "armor_equipped": True}
    assert dr.armor_ratings(c, {})["ratings"]["chest"] == 22
    bare = dr.damage_resistance(35, 0, dr.armor_ratings({}, ARMORS))
    assert {slot: row["total"] for slot, row in bare.items()} == {s: 3 for s in dr.SLOTS}
