import json
from pathlib import Path

import pytest

from src.models import energy_shields as es

DATA = Path(__file__).resolve().parent.parent / "data" / "core" / "equipment"
ARMORS = {
    "Mark VI Powered Assault Armor": {"energy_shields": {"integrity": 125, "delay": 2, "recharge": 50}},
    "Mark IV Powered Assault Armor": {},
    "Headhunter Variant Mark II Semi-Powered Infiltration Armor": {
        "energy_shields": {"integrity": 75, "delay": 3, "recharge": 25},
        "traits": [{"name": es.SPI_TRAIT, "description": "..."}],
    },
}
LOOT = {"rarity": "Rare", "material": "Plasteel", "armor_values": {"head": 20, "arms": 21, "chest": 22, "legs": 21}}


def spartan(armor="Mark VI Powered Assault Armor", **extra):
    return {"soldier_type": "UNSC / ONI Spartan II Augmented Soldier", "armor": armor, "armor_equipped": True, **extra}


def guardian(**extra):
    return {"soldier_type": "Titan Class Soldier Type", **extra}


@pytest.mark.parametrize("text,expected", [
    ("this suit grants the Character +50 to Shield Integrity and +25 to Shield Recharge.",
     {"integrity": 50, "recharge": 25}),
    ("The Recon Suit's increased Shields of +20 Shield Integrity also gives the suit a -2 Penalty to Armor.",
     {"integrity": 20}),
    ("gives the User a +25 Bonus to Shield Integrity, as well as +10 to Shield Recharge Rate.",
     {"integrity": 25, "recharge": 10}),
    ("The suit offers +10 to Camouflage Tests and gives +20 to the Shields of the user.", {"integrity": 20}),
    ("Gives a +5 to Strength and Agility, a +1 to Mythic Strength, and a +25 to Energy Shield Integrity.",
     {"integrity": 25}),
    ("Deadeye has -4 to all Armor Locations.", {}),
])
def test_variant_shield_modifiers(text, expected):
    assert es.variant_shield_modifiers(text) == expected


def test_armor_data_matches_the_book():
    doc = json.loads((DATA / "unsc_armor.json").read_text(encoding="utf-8"))
    records = {r["name"]: r for group in doc[next(iter(doc))].values() for r in group}
    book = {  # Mythic 7.0 CU1 armor tables
        "Mark V Powered Assault Armor": (125, 3, 25),
        "Mark VI Powered Assault Armor": (125, 2, 50),
        "GEN II Powered Armor": (150, 2, 50),
        "GEN III Powered Armor": (175, 2, 50),
        "Headhunter Variant Mark II Semi-Powered Infiltration Armor": (75, 3, 25),
    }
    for name, (integrity, delay, recharge) in book.items():
        assert records[name]["energy_shields"] == {"integrity": integrity, "delay": delay, "recharge": recharge}
    assert "energy_shields" not in records["Mark IV Powered Assault Armor"]


def test_core_shield_from_armor():
    shield = es.energy_shield(spartan(), ARMORS, "Core")
    assert (shield["has_shield"], shield["integrity"], shield["delay"], shield["recharge"]) == (True, 125, 2, 50)
    assert shield["source"] == "Mark VI Powered Assault Armor"


def test_armor_without_shields_or_removed():
    assert not es.energy_shield(spartan("Mark IV Powered Assault Armor"), ARMORS, "Core")["has_shield"]
    removed = es.energy_shield(spartan(armor_equipped=False), ARMORS, "Core")
    assert not removed["has_shield"] and "removed" in removed["notes"][0]


def test_variant_and_other_integrity():
    c = spartan(armor_variant={"name": "Grenadier", "generation": "GEN I",
                               "description": "+50 to Shield Integrity and +25 to Shield Recharge."})
    shield = es.energy_shield(c, ARMORS, "Core", other_integrity=10)
    assert (shield["integrity"], shield["recharge"], shield["delay"]) == (185, 75, 2)


def test_spi_photo_reactive_panels():
    c = spartan("Headhunter Variant Mark II Semi-Powered Infiltration Armor")
    assert es.energy_shield(c, ARMORS, "Core")["recharge"] == 25
    active = es.energy_shield(c, ARMORS, "Core", panels_active=True)
    assert (active["recharge"], active["delay"]) == (12, 6)


def test_light_shielding_needs_guardian_armor():
    worn = guardian(armor="Rare Plasteel Armor Set", armor_loot=LOOT, armor_equipped=True)
    shield = es.energy_shield(worn, {}, "Light & Sky")
    assert (shield["integrity"], shield["delay"], shield["recharge"]) == (125, 5, 50)
    assert "Light Shielding" in shield["source"]
    assert not es.energy_shield(guardian(), {}, "Light & Sky")["has_shield"]
    # same armor outside Light & Sky, or worn by a non-Guardian: no Light Shielding
    assert not es.energy_shield(worn, {}, "Core")["has_shield"]
    assert not es.energy_shield(dict(worn, soldier_type="Marine"), {}, "Light & Sky")["has_shield"]


def test_recharge_caps_at_integrity():
    shield = {"integrity": 125, "recharge": 50}
    assert es.recharge(30, shield) == 80
    assert es.recharge(100, shield) == 125
