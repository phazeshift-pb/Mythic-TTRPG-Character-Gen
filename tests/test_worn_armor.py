"""Worn armor bonuses apply to effective stats only while armor is equipped."""
from src.data_loader import DataLoader
from src.models import worn_armor
from src.models.equipment_packs import armor_index


def _setup():
    data = DataLoader().load_all()
    return data, armor_index(data)


def _character(**extra):
    base = {
        "armor": "GEN II Powered Armor",
        "characteristics": {"STR": 45, "TOU": 45, "AGI": 40, "PER": 30},
        "mythic_characteristics": {"STR": "+5", "TOU": "+4", "AGI": "+3"},
    }
    base.update(extra)
    return base


def test_spartan_iv_gen_ii_bonuses_apply_when_equipped():
    data, armors = _setup()
    soldier = data.get("soldier_type", "spartan_iv")
    effective = worn_armor.effective_character(_character(), armors, soldier)
    assert effective["characteristics"] == {"STR": 70, "TOU": 50, "AGI": 60, "PER": 30}
    assert effective["mythic_characteristics"] == {"STR": 9, "TOU": "+4", "AGI": 7}


def test_unequipped_armor_leaves_stats_untouched():
    data, armors = _setup()
    soldier = data.get("soldier_type", "spartan_iv")
    character = _character(armor_equipped=False)
    effective = worn_armor.effective_character(character, armors, soldier)
    assert effective["characteristics"] == character["characteristics"]
    assert effective["mythic_characteristics"] == character["mythic_characteristics"]


def test_equipped_defaults_true_only_when_there_is_armor():
    assert worn_armor.is_equipped({"armor": "M52B Standard"}) is True
    assert worn_armor.is_equipped({"armor": None, "armor_equipped": True}) is False


def test_bdu_penalties_apply_and_plain_bdus_change_nothing():
    _, armors = _setup()
    eod = worn_armor.effective_character(_character(armor="ED4 E.O.D"), armors)
    assert eod["characteristics"]["AGI"] == 30
    assert worn_armor.armor_bonus({"armor": "ODST Personal Protection"}, armors) == {"AGI": -10}
    plain = worn_armor.effective_character(_character(armor="M52B Standard"), armors)
    assert plain["characteristics"]["AGI"] == 40


def test_saved_bonus_is_used_when_armor_data_is_missing():
    character = _character(armor="Homebrew Suit", armor_bonus={"STR": 10, "mythic_AGI": 1})
    effective = worn_armor.effective_character(character, {})
    assert effective["characteristics"]["STR"] == 55
    assert effective["mythic_characteristics"]["AGI"] == 4
