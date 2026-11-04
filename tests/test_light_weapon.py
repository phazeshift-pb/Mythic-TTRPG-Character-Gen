"""Light Weapon builder rules: weapon list, effects, costs and saved builds."""
import random

import pytest

from src.data_loader import DataLoader
from src.models import light_weapon
from src.models.light_loadout import LightLoadout
from src.models.light_weapon import LightWeaponRules, add_damage_dice, add_modifier, light_cost_for


@pytest.fixture(scope="module")
def lns_data():
    return DataLoader(use_light_and_sky=True).load_all()


@pytest.fixture(scope="module")
def rules(lns_data):
    return LightWeaponRules(lns_data)


def guardian(**extra):
    character = {
        "soldier_type": "Titan Class Soldier Type",
        "connections": ["Solar"],
        "characteristics": {"WFM": 43, "WFR": 37},
        "light_abilities": [],
        "supers": [],
    }
    character.update(extra)
    return character


def test_light_cost_rounds_up_to_five():
    assert [light_cost_for(cost) for cost in (0, 5, 17, 28, 33, 40, 77, 132)] == [
        0, 5, 20, 30, 35, 40, 80, 135,
    ]


def test_catalog_has_every_melee_weapon_shield_and_ranged_type(rules):
    assert len(rules.weapons(light_weapon.MELEE)) == 47
    assert len(rules.weapons(light_weapon.SHIELD)) == 4
    ranged = rules.weapons(light_weapon.RANGED)
    assert len(ranged) == 20 and all(len(weapon.rows) == 10 for weapon in ranged)
    assert rules.weapon("melee:Kukri").light_cost == 20
    assert rules.weapon("melee:Superheavy Shield").light_cost == 135
    hand_cannon = rules.weapon("ranged:hand_cannons")
    assert (hand_cannon.name, hand_cannon.cost_cr, hand_cannon.light_cost) == ("Hand Cannon", 33, 35)


def test_damage_dice_and_warfare_modifier_text():
    assert add_damage_dice("3D10", 1) == "4D10"
    assert add_damage_dice("1D5", 2) == "1D5 +2D10"
    assert add_damage_dice(None, 1) == "1D10"
    assert add_modifier("4 +Full Strength Modifier", 4, "Warfare Melee") == "8 +Full Strength Modifier"
    assert add_modifier("13 + FSM", 2, "Warfare Melee") == "15 + FSM"
    assert add_modifier(None, 3, "Warfare Melee") == "3"
    assert add_modifier("12", None, "Warfare Range") == "12 +Warfare Range Modifier"


def test_effects_are_universal_plus_one_connection(rules):
    effects = rules.effects_for("Solar", guardian())
    connections = {effect.connection for effect in effects}
    assert connections == {"Universal", "Solar"}
    prismatic = rules.effects_for("Solar", guardian(connections=["Arc", "Stasis", "Prismatic"]))
    assert {"Universal", "Arc", "Solar", "Void", "Stasis", "Strand"} <= {
        effect.connection for effect in prismatic
    }


def test_connection_options(rules):
    assert rules.connection_options(guardian(connections=["Arc", "Strand"])) == ["Arc", "Strand"]
    assert rules.connection_options(guardian(connections=["Prismatic"])) == [
        "Arc", "Solar", "Void", "Stasis", "Strand",
    ]


def test_light_ability_doubles_effect_energy(rules):
    kukri = rules.weapon("melee:Kukri")
    # Thrown duplicates x3 (+5 each) and Solar Flame (+5): 20 listed, doubled = 40
    build = rules.build(kukri, "Solar", False, [("universal:5", 3), ("solar:2", 1)], character=guardian())
    assert build["light_cost"] == 20
    assert build["energy_per_turn"] == 20 + 40
    assert build["experience_cost"] == 500
    stats = build["stats"]
    assert stats["damage"] == "3D10"  # 2D10 +1D10
    assert stats["bonus_damage"] == "13 +Half Strength Modifier"  # 9 + WFM modifier 4
    assert stats["pierce"] == "11 +Half Strength Modifier"
    assert "Special Damage on 9 or 10" in stats["special_rules"]
    assert build["name"] == "Light Weapon: Solar Kukri"


def test_super_doubles_light_cost_and_adds_listed_effect_energy(rules):
    hand_cannon = rules.weapon("ranged:hand_cannons")
    build = rules.build(hand_cannon, "Solar", True, [("solar:0", 1)], row_index=4, character=guardian())
    assert build["energy_per_turn"] == 35 * 2 + 10
    assert build["experience_cost"] == 750
    row = hand_cannon.rows[4]
    assert build["stats"]["damage"] == add_damage_dice(row["damage"], 2)
    assert build["stats"]["warfare"] == "WFR"
    assert build["weapon"]["roll"] == "41-50"
    assert any("No ammunition" in rule for rule in build["stats"]["special_rules"])


def test_glaive_uses_warfare_melee(rules):
    build = rules.build(rules.weapon("ranged:glaives"), "Solar", False, row_index=0, character=guardian())
    assert build["stats"]["warfare"] == "WFM"


def test_build_rejects_other_connections_and_too_many_effects(rules):
    kukri = rules.weapon("melee:Kukri")
    with pytest.raises(ValueError, match="Arc"):
        rules.build(kukri, "Solar", True, [("arc:0", 1)], character=guardian())
    five = [(f"universal:{index}", 1) for index in range(5)]
    with pytest.raises(ValueError, match="at most 4"):
        rules.build(kukri, "Solar", True, five, character=guardian())


def test_counted_effect_is_capped(rules):
    build = rules.build(rules.weapon("melee:Kukri"), "Solar", True, [("universal:5", 99)])
    assert build["effects"][0]["count"] == light_weapon.MAX_EFFECT_COUNT


def test_roll_row():
    roll, index = LightWeaponRules.roll_row(random.Random(3))
    assert 1 <= roll <= 100 and index == (roll - 1) // 10


def test_builds_can_be_taken_many_times(rules):
    character = guardian()
    kukri = rules.weapon("melee:Kukri")
    first = light_weapon.add_build(character, rules.build(kukri, "Solar", False))
    second = light_weapon.add_build(character, rules.build(kukri, "Solar", False))
    as_super = light_weapon.add_build(character, rules.build(kukri, "Solar", True))
    assert [first["name"], second["name"]] == ["Light Weapon: Solar Kukri", "Light Weapon: Solar Kukri (2)"]
    assert character["light_abilities"] == [first["name"], second["name"]]
    assert character["supers"] == [as_super["name"]] == ["Light Weapon Super: Solar Kukri"]
    assert len(character["light_weapons"]) == 3
    light_weapon.remove_build(character, second["name"])
    assert character["light_abilities"] == [first["name"]]
    assert len(light_weapon.builds(character)) == 2


def test_light_page_shows_build_energy(lns_data, rules):
    character = guardian()
    kukri = rules.weapon("melee:Kukri")
    regular = light_weapon.add_build(
        character, rules.build(kukri, "Solar", False, [("solar:2", 1)])
    )
    super_build = light_weapon.add_build(
        character, rules.build(kukri, "Solar", True, [("solar:2", 1)])
    )
    loadout = LightLoadout(character, lns_data)
    state = loadout.loadout()
    assert regular["name"] in state["abilities"] and state["super"] == super_build["name"]
    assert loadout.power(regular["name"]).energy_cost() == 30  # 20 + 2 x 5
    power = loadout.power(super_build["name"])
    assert power.energy_cost(as_super=True) == 45  # 20 x 2 + 5, not doubled again
    assert power.stats and "Flame" in power.super_description
