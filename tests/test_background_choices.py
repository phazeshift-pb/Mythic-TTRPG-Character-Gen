import pytest

from src.data_loader import DataLoader
from src.generator.character_generator import CharacterGenerator
from src.models.background_choices import choice_groups, describe, resolve_modifiers
from src.models.character import CHAR_CODES, Character


@pytest.fixture(scope="module")
def core():
    return DataLoader().load_all()


def record(core, family, name):
    return next(r for r in core.get(family, family)[family] if r["name"] == name)


def blank():
    c = Character()
    c.characteristics = {code: 30 for code in CHAR_CODES}
    return c


def test_every_environment_is_one_bonus_and_one_penalty(core):
    for env in core.get("environment", "environment")["environment"]:
        groups = choice_groups(env)
        assert [g["section"] for g in groups] == ["bonuses", "penalties"], env["name"]
        assert all(len(g["labels"]) == 3 for g in groups)


def test_city_applies_only_the_picked_options(core):
    c = blank()
    c.apply_environment(record(core, "environment", "City"), ["+5 Courage", "-5 Toughness"])
    changed = {k: v - 30 for k, v in c.characteristics.items() if v != 30}
    assert changed == {"CRG": 5, "TOU": -5}


def test_laborer_option_is_a_pair(core):
    c = blank()
    c.apply_upbringing(
        record(core, "upbringing", "Laborer"),
        ["+1 Strength and +2 Toughness", "-3 Leadership"],
    )
    assert (c.characteristics["STR"], c.characteristics["TOU"]) == (31, 32)
    assert c.characteristics["LDR"] == 27 and c.characteristics["CRG"] == 30


def test_fixed_modifiers_still_apply(core):
    c = blank()
    c.apply_upbringing(record(core, "upbringing", "Nobility"))
    assert c.characteristics["CHA"] == 35 and c.characteristics["TOU"] == 25


def test_street_urchin_adds_two_wounds(core):
    c = blank()
    c.apply_upbringing(record(core, "upbringing", "Street Urchin"), ["-1 Intellect"])
    c.compute_wounds()
    assert c.wounds_modifier == 2
    assert c.wounds == 40 + 3 * 2 + 2
    assert c.characteristics["INT"] == 29 and c.characteristics["STR"] == 30


def test_missing_choice_applies_nothing_and_is_logged(core):
    c = blank()
    c.apply_environment(record(core, "environment", "City"), [])
    assert all(v == 30 for v in c.characteristics.values())
    assert sum("no valid choice" in line for line in c.debug_log) == 2


def test_resolve_and_describe():
    rec = {"name": "X", "bonuses": ["+1 Strength", {"choose_one": ["+2 Agility", "+2 Courage"]}]}
    assert resolve_modifiers(rec, ["+2 Courage"]) == (["+1 Strength", "+2 Courage"], [])
    assert describe(rec["bonuses"]) == ["+1 Strength", "+2 Agility or +2 Courage"]


def test_generator_threads_choices_through(core):
    soldier = core.list("soldier_type")[0]
    gen = CharacterGenerator(core, use_light_and_sky=False)
    plain = gen.generate(name="A", soldier_type=soldier)
    picked = gen.generate(
        name="B",
        soldier_type=soldier,
        upbringing="Aristocracy",
        environment="Town",
        upbringing_choices=["+5 Charisma", "-5 Agility"],
        environment_choices=["+5 Charisma", "-5 Intellect"],
    )
    diff = {k: picked.characteristics[k] - plain.characteristics[k] for k in CHAR_CODES}
    assert {k: v for k, v in diff.items() if v} == {"CHA": 10, "AGI": -5, "INT": -5}


def _lifestyle(core, name):
    return record(core, "lifestyle", name)


def test_hunter_asks_after_the_roll(core):
    asked = []

    def choose(rec, roll, groups):
        asked.append((rec["name"], roll, [g["labels"] for g in groups]))
        return ["+3 Warfare Melee"]

    c = blank()
    c.apply_lifestyle(_lifestyle(core, "Hunter"), 7, choose)
    assert asked == [("Hunter", 7, [["+3 Warfare Range", "+3 Warfare Melee"]])]
    assert c.characteristics["WFM"] == 33 and c.characteristics["CRG"] == 27
    assert c.lifestyle_results == [{"name": "Hunter", "roll": 7, "choices": ["+3 Warfare Melee"]}]


def test_weapon_training_low_roll_is_plus_one_minus_the_other(core):
    c = blank()
    c.apply_lifestyle(
        _lifestyle(core, "Weapon Training"), 3,
        lambda r, roll, g: ["+5 Warfare Range and -5 Warfare Melee"],
    )
    assert (c.characteristics["WFR"], c.characteristics["WFM"]) == (35, 25)


def test_wise_guy_only_asks_on_a_ten(core):
    calls = []
    c = blank()
    c.apply_lifestyle(_lifestyle(core, "Wise Guy"), 5, lambda *a: calls.append(a) or [])
    assert calls == [] and c.characteristics["INT"] == 32
    c.apply_lifestyle(_lifestyle(core, "Wise Guy"), 10, lambda r, roll, g: ["-5 Warfare Range"])
    assert c.characteristics["WFR"] == 25 and c.characteristics["INT"] == 37


def test_generator_passes_lifestyle_callback_and_can_be_cancelled(core):
    soldier = core.list("soldier_type")[0]
    gen = CharacterGenerator(core, use_light_and_sky=False)
    char = gen.generate(
        name="H", soldier_type=soldier, lifestyles=["Hunter", "Hunter", "Hunter"],
        lifestyle_choice=lambda r, roll, g: ["+3 Warfare Range"],
    )
    assert len(char.lifestyle_results) == 3
    assert all(r["choices"] == ["+3 Warfare Range"] for r in char.lifestyle_results)

    class Cancelled(Exception):
        pass

    def cancel(*_):
        raise Cancelled()

    with pytest.raises(Cancelled):
        gen.generate(name="X", soldier_type=soldier, lifestyles=["Hunter"], lifestyle_choice=cancel)
