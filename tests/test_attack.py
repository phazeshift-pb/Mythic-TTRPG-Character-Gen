import pytest

from src.models import attack as a

ARMORY = {
    "MA5C ICWS Assault Rifle": {
        "weapon_type": "Rifle", "tags": ["UD", "TH"], "rate_of_fire": "Semi-Auto (2), Auto (6), Burst (2)",
        "range": "30m-1,400m", "_group": "rifles", "_family": "unsc_weapons",
    },
    "M6 Pistol": {"weapon_type": "Pistol", "tags": ["OH"], "rate_of_fire": "Semi-Auto (2)", "range": "20m-100m",
                  "_group": "pistols", "_family": "unsc_weapons"},
    "M1 Combat Knife": {"weapon_type": "Knife", "tags": ["PD", "DW"], "reach": None, "_group": "melee_weapons",
                        "_family": "unsc_weapons"},
    "AIE-486H": {"weapon_type": "Heavy Machine Gun", "tags": ["I", "UD", "TH", "HW"], "rate_of_fire": "Auto (10)",
                 "range": "40m-1,200m", "_group": "machine_guns", "_family": "unsc_weapons"},
    "M9 Frag": {"weapon_type": "Grenade", "tags": ["UD"], "_group": "grenades", "_family": "unsc_explosives"},
    "SRS99": {"weapon_type": "Sniper Rifle", "tags": ["TH"], "rate_of_fire": "Semi-Auto (1)",
              "range": "100m-2,400m", "_group": "sniper_rifles", "_family": "unsc_weapons"},
}
TRAINING = {"weapon_training": {"training": [
    {"name": "Basic", "weapons": ["Pistol", "Knife", "Shotgun"]},
    {"name": "Infantry", "weapons": ["Rifle", "Carbine", "SMG", "Grenade"]},
    {"name": "Heavy", "weapons": ["LMG", "MG", "HMG"]},
    {"name": "Melee", "weapons": ["All non-knife melee weapons", "Physical Shields"]},
]}}


def profile(name):
    return a.weapon_profile({"name": name}, ARMORY)


def total(name, **options):
    options.setdefault("characteristic", 40)
    return a.attack_target(profile(name), a.AttackOptions(**options))


def test_weapon_kinds_and_characteristic():
    assert profile("MA5C ICWS Assault Rifle").default_mode == a.FIRE
    assert profile("M1 Combat Knife").default_mode == a.MELEE
    assert profile("M9 Frag").modes == [a.THROW]
    assert a.weapon_profile(a.UNARMED).modes == [a.MELEE]
    assert total("M1 Combat Knife", mode=a.MELEE).characteristic_name == "WFM"
    assert total("M6 Pistol", mode=a.FIRE).characteristic_name == "WFR"
    assert total("M9 Frag", mode=a.THROW).characteristic_name == "WFM"


def test_loot_weapon_uses_its_rolled_stats():
    loot = {"name": "Rare Solar Pulse Rifle", "loot": {"weapon_type": "Pulse Rifle", "rate_of_fire": "Burst (3)",
                                                         "range": "20m-500m", "tags": ["TH"]}}
    p = a.weapon_profile(loot, ARMORY)
    assert p.kind == "firearm" and p.fire_modes[0].bonus == 10 and p.ranges == (20, 500)


@pytest.mark.parametrize("mode,bonus", [(0, 10), (1, 0), (2, 10)])
def test_fire_rate_bonus(mode, bonus):
    fire_mode = profile("MA5C ICWS Assault Rifle").fire_modes[mode]
    assert total("MA5C ICWS Assault Rifle", fire_mode=fire_mode).total == 40 + bonus


def test_range_bands():
    keys = {key: value for key, _, value in a.range_bands(profile("M6 Pistol"), a.FIRE)}
    assert keys == {"point_blank": 20, "close": 5, "optimal": 0, "long": -40, "extreme": -80}
    assert total("M6 Pistol", range_band="long").total == 0
    assert total("M1 Combat Knife", mode=a.MELEE, range_band="point_blank").total == 50


def test_marksman_halves_long_range_for_sniper_rifles_only():
    assert total("SRS99", range_band="extreme", abilities={"Marksman"}).total == 0
    assert [n for n, _, _ in a.relevant_abilities({"Marksman"}, profile("M6 Pistol"), a.FIRE)] == []


def test_called_shots_and_halving_abilities():
    assert total("M6 Pistol", called_shot=True).total == 10
    assert total("M6 Pistol", called_shot=True, called_target="sublocation").total == -20
    assert total("M6 Pistol", called_shot=True, abilities={"Clear Target"}).total == 25
    knife = dict(mode=a.MELEE, called_shot=True)
    assert total("M1 Combat Knife", abilities={"Clear Target"}, **knife).total == 10
    assert total("M1 Combat Knife", abilities={"Precision Strike"}, **knife).total == 25


def test_aim_steady_aim_and_laser():
    assert total("M6 Pistol", aim="half").total == 45
    assert total("M6 Pistol", aim="full", abilities={"Steady Aim"}).total == 60
    assert total("M6 Pistol", laser=True).total == 45
    assert total("M6 Pistol", aim="full", laser=True).total == 50  # no stacking
    assert total("M6 Pistol", aim="full", blind_fire="blind").total == -20  # Blind Fire gets no Aim
    assert total("M6 Pistol", aim="full", blind_fire="smartlink").total == 20


def test_wielding_penalties_and_mythic_strength():
    assert total("M6 Pistol", wielding="one").total == 30
    assert total("M6 Pistol", wielding="dual").total == 20
    assert total("M6 Pistol", wielding="dual", mythic_strength=1).total == 25
    assert total("M6 Pistol", wielding="dual", mythic_strength=4).total == 30  # minimum 10
    assert total("M6 Pistol", wielding="dual", abilities={"Akimbo"}).total == 30
    # base [DW] melee weapons can drop to 0
    assert total("M1 Combat Knife", mode=a.MELEE, wielding="dual", mythic_strength=2).total == 40


def test_heavy_weapon_bracing():
    assert profile("AIE-486H").wield_tag == "HW"
    assert total("AIE-486H").total == 20
    assert total("AIE-486H", braced=True).total == 40
    assert total("AIE-486H", braced=True, wielding="one").total == 20


def test_movement_and_movement_abilities():
    assert total("M6 Pistol", movement="run").total == 0
    assert total("M6 Pistol", movement="run", abilities={"Mobile Fire"}).total == 10
    assert total("M1 Combat Knife", mode=a.MELEE, movement="charge").total == 50
    assert total("M6 Pistol", movement="charge", abilities={"Aggressive Advance"}).total == 40
    assert total("M6 Pistol", movement="charge", abilities={"Aggressive Advance"}, first_charge_shot=False).total == 10


def test_thrown_weapons():
    assert total("M9 Frag", mode=a.THROW).total == 40
    assert total("M1 Combat Knife", mode=a.THROW).total == 35
    assert total("M6 Pistol", mode=a.THROW).total == 10
    assert total("M6 Pistol", mode=a.THROW, abilities={"Faster Than Reloading"}).total == 40


def test_conditions():
    assert total("M6 Pistol", lighting="darkness").total == -10
    assert total("M6 Pistol", lighting="darkness", abilities={"Blind Fight"}).total == 15
    assert total("M1 Combat Knife", mode=a.MELEE, weather="severe").total == 25  # melee takes half
    assert total("M6 Pistol", target_stance="prone").total == 30
    assert total("M1 Combat Knife", mode=a.MELEE, target_stance="prone").total == 50
    assert total("M6 Pistol", target_size="great").total == 60
    assert total("SRS99", speed="200").total == 40 - 10  # sniper rifles halve speed penalties
    assert total("M6 Pistol", speed="200").total == 20
    assert total("M6 Pistol", perceptive="triple").total == -20


def test_situational_checks_only_apply_to_matching_modes():
    assert total("M6 Pistol", situational={"into_melee", "outnumbering"}).total == 20
    assert total("M1 Combat Knife", mode=a.MELEE, situational={"into_melee", "outnumbering"}).total == 50


def test_melee_ability_bonuses():
    owned = {"Hand-To-Hand Basic", "Modern Army Combative"}
    assert total("M1 Combat Knife", mode=a.MELEE, abilities=owned).total == 50
    assert total("M6 Pistol", abilities=owned).total == 40


def test_weapon_training():
    assert a.is_untrained(profile("AIE-486H"), {"Basic", "Infantry"}, TRAINING) is True
    assert a.is_untrained(profile("MA5C ICWS Assault Rifle"), {"Infantry"}, TRAINING) is False
    assert a.is_untrained(a.weapon_profile(a.UNARMED), set(), TRAINING) is False
    assert total("AIE-486H", braced=True, situational={"untrained"}).total == 20


def test_breakdown_lists_each_modifier():
    result = total("M6 Pistol", fire_mode=profile("M6 Pistol").fire_modes[0], aim="half", custom=-7)
    assert result.modifiers == [("Semi-Auto fire", 10), ("Half Aim", 5), ("Other / GM modifier", -7)]
    assert result.total == 48 and result.total_modifier == 8
