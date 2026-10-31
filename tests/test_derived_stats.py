import json
import re
from pathlib import Path

import pytest

from src.models.character import Character, CHAR_CODES
from src.models import derived_stats as ds

DATA = Path(__file__).resolve().parent.parent / "data" / "character_creation"


def test_characteristic_modifier():
    assert ds.characteristic_modifier(25) == 2
    assert ds.characteristic_modifier(50) == 5
    assert ds.characteristic_modifier(9) == 0


@pytest.mark.parametrize("raw,expected", [("+3", 3), (2, 2), ("0", 0), (None, 0), ("x", 0)])
def test_mythic_value(raw, expected):
    assert ds.mythic_value(raw) == expected


def test_max_wounds_matches_data_examples():
    doc = json.loads((DATA / "wounds_formula.json").read_text())["wounds_formula"]
    for ex in doc["examples"]:
        assert ds.max_wounds(ex["toughness"], ex["mythic_toughness"]) == int(
            ex["calculated_wounds"].rsplit("=", 1)[1]
        )


def test_robust_adds_wounds():
    assert ds.max_wounds(50, 0, 1) == ds.max_wounds(50, 0) + 18


def test_constants_match_data_files():
    formula = json.loads((DATA / "wounds_formula.json").read_text())["wounds_formula"]["formula"]
    assert formula["base"] == ds.WOUNDS_BASE
    assert int(re.findall(r"\d+", formula["toughness_modifier"])[-1]) == ds.WOUNDS_PER_TOUGHNESS_MODIFIER
    assert int(re.findall(r"\d+", formula["mythic_toughness"])[-1]) == ds.WOUNDS_PER_MYTHIC_TOUGHNESS
    outliers = json.loads((DATA / "outliers.json").read_text())["outliers"]["list"]
    robust = next(o for o in outliers if o["name"] == "Robust")
    assert int(re.search(r"\+(\d+)", robust["effect"]).group(1)) == ds.ROBUST_WOUNDS


def test_fatigue_coma_threshold():
    assert ds.fatigue_coma_threshold(50) == 10


def _character(tou=50, mythic_tou="+3"):
    c = Character()
    c.characteristics = {code: 25 for code in CHAR_CODES}
    c.characteristics["TOU"] = tou
    c.mythic_characteristics = {"TOU": mythic_tou}
    return c


def test_character_compute_wounds_and_fatigue():
    c = _character()
    c.finalize()
    assert c.wounds == 40 + 5 * 2 + 3 * 2
    assert c.fatigue == 0


def test_apply_outlier_robust_recomputes_wounds():
    c = _character()
    c.finalize()
    before = c.wounds
    c.apply_outlier({"name": "Robust", "effect": "+18 Wounds."}, 0)
    assert c.wounds == before + 18
